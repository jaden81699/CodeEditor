import os
import subprocess
import tempfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from editor.forms import QuestionsForm, TestCaseFormSet
from editor.models import Questions, ParticipantProfile, Submission


@login_required
def editor(request):
    # 1️⃣ Fetch the user’s profile & cohort
    profile = request.user.participantprofile
    is_experimental = (profile.group == ParticipantProfile.EXPERIMENTAL)

    # 2️⃣ Detect redo mode via ?redo=1 (only for Experimental cohort)
    redo_mode = (is_experimental and request.GET.get('redo') == '1')

    # 3️⃣ Build the question list
    if redo_mode:
        # Only those questions they got CORRECT on attempt 1 WITH AI
        passed_qids = Submission.objects.filter(
            user=request.user,
            attempt_no=1,
            used_ai=True,
            is_correct=True
        ).values_list('question_id', flat=True)

        # Preserve your desired ordering
        questions = list(
            Questions.objects
            .filter(id__in=passed_qids)
            .order_by('id')
        )
    else:
        # First pass: show the first 3 questions
        questions = list(
            Questions.objects
            .all()
            .order_by('id')[:3]
        )

    # 4️⃣ (Optional) Compute any scores you want to display
    # For example: first‑attempt correct count
    first_score = profile.first_attempt_correct
    second_score = profile.second_attempt_correct

    # 5️⃣ Render
    return render(request, 'editor.html', {
        'questions': questions,
        'is_experimental': is_experimental,
        'redo_mode': redo_mode,
        'first_score': first_score,
        'second_score': second_score,
    })


@require_POST
def run_code(request):
    """
    Compiles and executes Java code for a given question (I/O or unit test).
    Expects POST params:
      - code: the user’s Main.java source
      - question_id: the ID of the Questions object to run against
    Returns JSON: { results: [ { input, expected_output, actual_output, passed }, … ] }
    """
    code = request.POST.get("code", "").strip()
    qid = request.POST.get("question_id")

    # Basic validation
    if not code:
        return JsonResponse({"error": "No code provided."}, status=400)
    if not qid:
        return JsonResponse({"error": "No question_id provided."}, status=400)

    # Lookup question
    try:
        question = Questions.objects.get(pk=int(qid))
    except (Questions.DoesNotExist, ValueError):
        return JsonResponse({"error": "Invalid question_id."}, status=400)

    test_cases = question.test_cases.all()
    results = []

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1) Compile Main.java
            cp = compile_java_file(code, "Main.java", temp_dir)
            if cp.returncode != 0:
                return JsonResponse({"error": cp.stderr}, status=200)

            # 2) Branch on question type
            if question.question_type == "IO":
                # For each test case, run Main with test_input
                for tc in test_cases:
                    out = execute_java_file("Main", temp_dir, input_data=tc.test_input)
                    expected = tc.expected_output.strip()
                    actual = out.strip()
                    results.append({
                        "input": tc.test_input,
                        "expected_output": expected,
                        "actual_output": actual,
                        "passed": actual == expected
                    })

            else:
                # Unit test via your existing CountPositiveRunner.java
                runner_src = "/Users/jaden/PycharmProjects/CodeEditor/java/CountPositiveRunner.java"
                dest = os.path.join(temp_dir, "CountPositiveRunner.java")
                subprocess.run(["cp", runner_src, dest], check=True)

                # Compile the runner
                cr = subprocess.run(
                    ["javac", dest], capture_output=True, text=True
                )
                if cr.returncode != 0:
                    return JsonResponse({"error": cr.stderr}, status=200)

                # Run the runner
                out = execute_java_file("CountPositiveRunner", temp_dir)

                # Parse lines for “Actual:” prefix
                actual_val = None
                for line in out.splitlines():
                    if line.startswith("Actual:"):
                        actual_val = line.split("Actual:")[1].strip()
                        break

                expected_val = "6"
                passed = (actual_val == expected_val)
                results.append({
                    "input": None,
                    "expected_output": expected_val,
                    "actual_output": actual_val or out,
                    "passed": passed
                })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"results": results})


@login_required
def create_or_edit_questions(request, question_id=None):
    """Create or edit a coding question along with its test cases."""
    question = get_object_or_404(Questions, pk=question_id) if question_id else None

    if request.method == 'POST':
        q_form = QuestionsForm(request.POST, instance=question)
        formset = TestCaseFormSet(request.POST, instance=question)

        if q_form.is_valid() and formset.is_valid():
            saved_question = q_form.save()
            formset.instance = saved_question
            formset.save()
            return redirect('create-or-edit-questions')
        else:
            print("q_form errors:", q_form.errors)
            print("formset errors:", formset.errors)

    q_form = QuestionsForm(instance=question)
    formset = TestCaseFormSet(instance=question)
    questions = Questions.objects.all()

    return render(request, 'create-or-edit-questions.html', {
        'q_form': q_form,
        'formset': formset,
        'question': question,
        'questions': questions,
    })


@login_required
def delete_question(request, question_id):
    """Delete a coding question."""
    question = get_object_or_404(Questions, pk=question_id)
    if request.method == 'POST':
        question.delete()
        return redirect('create-or-edit-questions')
    return render(request, 'confirm-delete.html', {'question': question})


def logout_view(request):
    """Logout user and redirect to login page."""
    logout(request)
    return redirect('login')


def submit_code(request):
    """
    Handle the user clicking "Submit":
    - Compile & run their Main.java for the given question.
    - Record a Submission (which question, attempt_no, used_ai, is_correct).
    - Update the profile's counters.
    - Redirect to either:
        • /editor/?redo=1  (experimental, first attempt)
        • /editor/         (all other cases)
    """
    # 1) Pull form data
    code = request.POST.get("code", "").strip()
    qid = request.POST.get("question_id")
    attempt_no = int(request.POST.get("attempt_no", "1"))

    if not code or not qid:
        return redirect("editor")

    # 2) Lookup objects
    question = get_object_or_404(Questions, pk=int(qid))
    profile = request.user.participantprofile

    # Determine if AI was visible:

    used_ai = (profile.group == ParticipantProfile.EXPERIMENTAL and attempt_no == 1)

    # 3) Compile & test
    is_correct = False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            # compile Main.java
            cpp = compile_java_file(code, "Main.java", tmp)
            if cpp.returncode == 0:
                if question.question_type == "IO":
                    # pass every I/O test
                    is_correct = all(
                        execute_java_file("Main", tmp, input_data=tc.test_input).strip()
                        == tc.expected_output.strip()
                        for tc in question.test_cases.all()
                    )
                else:
                    # unit test via existing CountPositiveRunner
                    runner_src = "/Users/jaden/PycharmProjects/CodeEditor/java/CountPositiveRunner.java"
                    dest = os.path.join(tmp, "CountPositiveRunner.java")
                    subprocess.run(["cp", runner_src, dest], check=True)

                    cr = subprocess.run(["javac", dest], capture_output=True, text=True)
                    if cr.returncode == 0:
                        output = execute_java_file("CountPositiveRunner", tmp).splitlines()
                        actual = None
                        for line in output:
                            if line.startswith("Actual:"):
                                actual = line.split("Actual:")[1].strip()
                                break
                        is_correct = (actual == "6")
    except Exception:
        is_correct = False

    # 4) Record the submission
    Submission.objects.create(
        user=request.user,
        question=question,
        attempt_no=attempt_no,
        used_ai=used_ai,
        is_correct=is_correct
    )

    # 5) Update the participant’s counters
    if attempt_no == 1:
        if is_correct:
            profile.first_attempt_correct += 1
        else:
            profile.first_attempt_incorrect += 1
    elif attempt_no == 2 and profile.group == ParticipantProfile.EXPERIMENTAL:
        if is_correct:
            profile.second_attempt_correct += 1

    profile.save()

    # 6) Redirect appropriately
    if profile.group == ParticipantProfile.EXPERIMENTAL and attempt_no == 1:
        # send them into "redo" mode
        return redirect(f"{reverse('editor')}?redo=1")
    else:
        # normal flow: next question (session logic inside editor() handles wrapping)
        return redirect("editor")


def compile_java_file(code, filename, temp_dir):
    """
    Writes Java code to a file, compiles it, and returns the process result.
    """
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, "w") as f:
        f.write(code)

    return subprocess.run(
        ["javac", file_path],
        capture_output=True,
        text=True
    )


def execute_java_file(class_name, temp_dir, input_data=None):
    """
    Runs a compiled Java file and returns its output.
    """
    try:
        run_process = subprocess.run(
            ["java", "-cp", temp_dir, class_name],
            input=input_data,
            capture_output=True,
            text=True
        )
        return run_process.stdout.strip() or run_process.stderr.strip()
    except Exception as e:
        return str(e)


def register(request):
    if request.method == 'POST':
        pwd1 = request.POST.get('password1')
        pwd2 = request.POST.get('password2')

        # Simple password confirmation check
        if not pwd1 or pwd1 != pwd2:
            return render(request, 'registration/login.html', {
                'register_error': 'Passwords must match and not be empty.'
            })

        # 1) Create a user with a temporary username
        user = User.objects.create_user(username='temp', password=pwd1)
        # 2) Grab its auto-incremented primary key
        new_username = str(user.id)
        # 3) Overwrite the username field
        user.username = new_username
        # 4) Save again
        user.save()

        # Optionally, log them in immediately
        # login(request, user)

        # 5) Render the same page, passing generated_username into context
        return render(request, 'registration/login.html', {
            'generated_username': new_username
        })

    # GET
    return render(request, 'registration/login.html')
