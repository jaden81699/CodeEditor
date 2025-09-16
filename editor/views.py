import json
import os
import subprocess
import tempfile
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout, login
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.utils.functional import cached_property
from django.contrib.auth.views import LoginView

from CodeEditor import settings
from editor.forms import QuestionsForm, TestCaseFormSet
from editor.models import Questions, ParticipantProfile, Submission


@login_required(login_url='experimental_app:login')
def editor(request):
    profile = request.user.participantprofile
    is_exp = (profile.group == ParticipantProfile.EXPERIMENTAL)

    # 1️⃣ Read which pass we're on (1 or 2)
    exp_pass = request.session.get("experimental_pass", 1)

    # 2️⃣ Pick questions + AI visibility
    if is_exp and exp_pass == 2:
        # second pass: only the kept questions
        keep_ids = request.session.get("experimental_keep_ids", [])
        questions = Questions.objects.filter(id__in=keep_ids).order_by("id")
        show_ai = False
    else:
        # first pass normal
        questions = Questions.objects.all().order_by("id")[:3]
        show_ai = True
        # and ensure we're set back to pass 1 if they just hit /editor/ manually
        request.session["experimental_pass"] = 1

    return render(request, "experimental_app/editor.html", {
        "questions": questions,
        "is_experimental": is_exp,
        "exp_pass": exp_pass,  # so your JS can do attempt_no = {{ exp_pass }}
        "show_ai": show_ai,
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

# @user_passes_test(lambda u: u.is_superuser)
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


@user_passes_test(lambda u: u.is_superuser)
def delete_question(request, question_id):
    """Delete a coding question."""
    question = get_object_or_404(Questions, pk=question_id)
    if request.method == 'POST':
        question.delete()
        return redirect('create-or-edit-questions')
    return render(request, 'confirm-delete.html', {'question': question})


@login_required
def submit_all(request):
    """
    Accepts a JSON payload:
      { "submissions": [
          { "question_id": 5, "code": "...", "attempt_no": 1 },
          { "question_id": 6, "code": "...", "attempt_no": 1 },
          { "question_id": 7, "code": "...", "attempt_no": 1 }
        ]
      }
    Runs through each, records Submission, updates counters, then returns:
      • next="second-pass", keep_ids=[…], hide_ai=True
      • or next="thank-you", redirect_url="/…"
    """
    payload = json.loads(request.body.decode('utf-8'))
    submissions = payload.get("submissions", [])
    user = request.user
    profile = request.user.participantprofile
    is_exp = (profile.group == ParticipantProfile.EXPERIMENTAL)

    question_ids = []  # will track the order
    passed_ids = []  # those that passed on this pass

    # 1) Compile, run & record each
    for item in submissions:
        qid = int(item["question_id"])
        code = item["code"]
        attempt = int(item["attempt_no"])
        question = get_object_or_404(Questions, pk=qid)

        # compile & run
        is_correct = False
        with tempfile.TemporaryDirectory() as tmp:
            compile_proc = compile_java_file(code, "Main.java", tmp)
            if compile_proc.returncode == 0:
                if question.question_type == "IO":
                    is_correct = all(
                        execute_java_file("Main", tmp, input_data=tc.test_input).strip()
                        == tc.expected_output.strip()
                        for tc in question.test_cases.all()
                    )
                else:
                    # unit‐test path
                    runner_src = "/Users/jaden/PycharmProjects/CodeEditor/java/CountPositiveRunner.java"
                    dest = os.path.join(tmp, "CountPositiveRunner.java")
                    subprocess.run(["cp", runner_src, dest], check=True)
                    compile_runner = subprocess.run(
                        ["javac", dest], capture_output=True, text=True
                    )
                    if compile_runner.returncode == 0:
                        out_lines = execute_java_file("CountPositiveRunner", tmp).splitlines()
                        actual = next(
                            (l.split("Actual:")[1].strip()
                             for l in out_lines if l.startswith("Actual:")),
                            None
                        )
                        is_correct = (actual == "6")
        print(f"[DEBUG]    → is_correct = {is_correct}")
        # record in DB
        Submission.objects.create(
            user=user,
            question=question,
            attempt_no=attempt,
            used_ai=(is_exp and attempt == 1),
            is_correct=is_correct
        )

        # update counters & passed_ids
        if attempt == 1:
            if is_correct:
                profile.first_attempt_correct += 1
                passed_ids.append(qid)
            else:
                profile.first_attempt_incorrect += 1
        else:
            # second pass only increments second_attempt_correct
            if is_correct and is_exp:
                profile.second_attempt_correct += 1
    print(f"[DEBUG] final passed_ids = {passed_ids}")
    profile.save()

    # 2) Decide what comes next
    # — experimental, first pass
    # make absolutely sure the client-sent attempt_no is an int
    exp_pass_num = request.session.get("experimental_pass", 1)

    if is_exp and exp_pass_num == 1:
        # no question passed on first attempt→ skip straight to thank you
        if not passed_ids:
            print("[DEBUG] No passed_ids → redirecting to thank-you")
            return JsonResponse({
                "status": "redirect",
                "redirect_url": reverse("experimental_app:thank-you")
            })

        # ★ store them in session for the second pass ★
        request.session['experimental_pass'] = 2
        request.session['experimental_keep_ids'] = passed_ids
        request.session.modified = True

        # some passed → do second-pass on those only
        profile.both_experimental_code_assessments_done = True
        #print(profile.both_experimental_code_assessments_done)
        return JsonResponse({
            "status": "next",
            "next": "second-pass",
            "keep_ids": passed_ids,
            "redirect_url": reverse("experimental_app:editor")
        })

    # — all other cases (second pass or non-experimental)
    profile.both_experimental_code_assessments_done = True
    profile.save()
    return JsonResponse({
        "status": "redirect",
        "redirect_url": reverse("post-assessment")
    })


@login_required
def post_assessment_questionnaire(request):
    # Guard: only allow after assessment is complete
    # Both control and experimental group will use this views function
    group_of_user = request.user.participantprofile.group
    profile = request.user.participantprofile
    if not (profile.both_experimental_code_assessments_done | profile.both_control_code_assessments_done):
        return HttpResponse("could not go through")  # or wherever your assessment lives

    qualtrics_link = settings.QUALTRICS_POSTASSESSMENT_LINK  # e.g. "https://yourdcid.qualtrics.com"
    # Pass identifiers you want to capture as Embedded Data in Qualtrics
    url = (
        f"{qualtrics_link}"
        f"?uid={request.user.pk}"
        f"&group={group_of_user}"
    )
    return redirect(url)


# @require_POST
# def submit_code(request):
#     """
#     1️⃣ First pass (attempt_no=1): AI available
#       - run & record every test
#       - mark used_ai=True
#       - set session['second_pass']=True
#       - return 200 OK (front-end will reload editor for pass 2)
#     2️⃣ Second pass (attempt_no=2): AI hidden
#       - run & record every test
#       - mark used_ai=False
#       - clear session['second_pass']
#       - return JSON { redirect: thank_you_url }
#     """
#     # pull your form fields
#     code = request.POST.get("code", "").strip()
#     qid = request.POST.get("question_id")
#     attempt_no = int(request.POST.get("attempt_no", "1"))
#
#     if not code or not qid:
#         return JsonResponse({"error": "Missing code or question_id"}, status=400)
#
#     # lookup
#     question = get_object_or_404(Questions, pk=int(qid))
#     profile = request.user.participantprofile
#
#     # compile & run exactly as before...
#     is_correct = False
#     try:
#         with tempfile.TemporaryDirectory() as tmp:
#             # write & compile Main.java
#             proc = compile_java_file(code, "Main.java", tmp)
#             if proc.returncode == 0:
#                 if question.question_type == "IO":
#                     is_correct = all(
#                         execute_java_file("Main", tmp, input_data=tc.test_input).strip()
#                         == tc.expected_output.strip()
#                         for tc in question.test_cases.all()
#                     )
#                 else:
#                     # compile & run your TestRunner…
#                     runner_src = "/path/to/CountPositiveRunner.java"
#                     dest = os.path.join(tmp, "CountPositiveRunner.java")
#                     subprocess.run(["cp", runner_src, dest], check=True)
#                     cr = subprocess.run(
#                         ["javac", dest], capture_output=True, text=True
#                     )
#                     if cr.returncode == 0:
#                         lines = execute_java_file("CountPositiveRunner", tmp).splitlines()
#                         actual = next(
#                             (l.split("Actual:")[1].strip() for l in lines if l.startswith("Actual:")),
#                             None
#                         )
#                         is_correct = (actual == "6")
#     except Exception:
#         is_correct = False
#
#     # decide AI-usage flag
#     used_ai = (attempt_no == 1)
#
#     # persist
#     Submission.objects.create(
#         user=request.user,
#         question=question,
#         attempt_no=attempt_no,
#         used_ai=used_ai,
#         is_correct=is_correct,
#     )
#
#     # update your profile counters if you like…
#
#     # now branch by attempt number
#     if attempt_no == 1:
#         # 1️⃣ First pass → mark session for second pass
#         request.session["second_pass"] = True
#         request.session.modified = True
#
#         # front-end will simply reload editor (no redirect in JSON)
#         return JsonResponse({"ok": True})
#
#     else:
#         # 2️⃣ Second pass → clear the flag, and send back a redirect
#         request.session.pop("second_pass", None)
#         thank_you = reverse("experimental_app:thank_you")
#         return JsonResponse({"redirect": thank_you})


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
    template = 'experimental_app/login_register_e.html'
    login_form = AuthenticationForm()
    context = {'form': login_form}

    if request.method == 'POST':
        pwd1 = request.POST.get('password1', '')
        pwd2 = request.POST.get('password2', '')

        if not pwd1 or pwd1 != pwd2:
            context['register_error'] = 'Passwords must match and not be empty.'
            return render(request, template, context)

        # create user with temp username
        user = User.objects.create_user(username='temp', password=pwd1)
        user.username = str(user.id)
        user.save()

        # Assign them to experimental group (update existing or create new)
        profile, created = ParticipantProfile.objects.get_or_create(user=user)
        profile.group = 'E'
        profile.save()

        # now tell the template to switch to the login tab
        context['generated_username'] = user.username
        return render(request, template, context)

    # GET just shows login+register tabs
    return render(request, template, context)


def thank_you(request):
    # clean up
    request.session.pop('experimental_pass', None)
    request.session.pop('experimental_keep_ids', None)
    return render(request, "experimental_app/thank_you.html")


def experimental_logout_view(request):
    """Logout user and redirect to login page."""
    logout(request)
    return redirect('experimental_app:login')


class ExperimentalLoginView(LoginView):
    template_name = "experimental_app/login_register_e.html"
    redirect_authenticated_user = True
    # once you’re logged in, go straight to your editor
    success_url = reverse_lazy("pre-assessment")

    def get_success_url(self):
        return self.success_url
