import os
import subprocess
import tempfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from editor.forms import QuestionsForm, TestCaseFormSet
from editor.models import Questions


def editor(request):
    """Display the code editor with the current question and user starter code."""
    questions = list(Questions.objects.all().order_by('id'))
    if not questions:
        return render(request, 'editor.html', {"error": "No questions available."})

    current_index = request.session.get("question_index", 0)
    score = request.session.get("correct_count", 0)

    if current_index >= len(questions):
        request.session["question_index"] = 0
        current_index = 0

    current_question = questions[current_index]

    return render(request, 'editor.html', {
        "question": current_question,
        "question_number": current_index + 1,
        "total_questions": len(questions),
        "score": score,
        "user_starter_code": current_question.user_starter_code,
    })


@require_POST
def run_code(request):
    """
    Compiles and executes Java code based on the question type (I/O or unit test).
    Returns JSON with execution results.
    """
    code = request.POST.get("code")
    if not code:
        return JsonResponse({"error": "No code provided."}, status=400)

    # Determine current question
    questions = list(Questions.objects.all().order_by("id"))
    if not questions:
        return JsonResponse({"error": "No questions available."}, status=400)

    current_index = request.session.get("question_index", 0)
    if current_index >= len(questions):
        request.session["question_index"] = 0
        current_index = 0

    current_question = questions[current_index]

    if request.POST.get("instructor_test_flag") is not None and True:
        question_id = request.POST.get("current_question_id_viewed_by_instructor")
        current_question = Questions.objects.get(id=question_id)

    test_cases = current_question.test_cases.all()
    results = []

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Compile user's Java code
            compile_process = compile_java_file(code, "Main.java", temp_dir)
            if compile_process.returncode != 0:
                return JsonResponse({"error": compile_process.stderr})

            # I/O Based Question Execution
            if current_question.question_type == "IO":
                for test in test_cases:
                    output = execute_java_file("Main", temp_dir, input_data=test.test_input)
                    results.append({
                        "input": test.test_input,
                        "expected_output": test.expected_output.strip(),
                        "actual_output": output,
                        "passed": output == test.expected_output.strip()
                    })
            else:
                # Unit Test Execution Using Predefined Test Runner
                test_runner_path = "/Users/jaden/PycharmProjects/CodeEditor/java/CountPositiveRunner.java"
                copied_test_runner_path = os.path.join(temp_dir, "CountPositiveRunner.java")
                subprocess.run(["cp", test_runner_path, copied_test_runner_path])

                compile_runner = subprocess.run(
                    ["javac", copied_test_runner_path],
                    capture_output=True,
                    text=True
                )
                if compile_runner.returncode != 0:
                    return JsonResponse({"error": compile_runner.stderr})

                # Run the test runner
                output = execute_java_file("CountPositiveRunner", temp_dir)

                # Extract "Actual" value from output
                actual_value = None
                for line in output.splitlines():
                    if line.startswith("Actual:"):
                        actual_value = line.replace("Actual:", "").strip()

                expected_value = "6"
                passed = actual_value == expected_value if actual_value else False
                results.append({
                    "expected_output": expected_value,
                    "actual_output": actual_value if actual_value else output,
                    "passed": passed
                })
    except Exception as e:
        return JsonResponse({"error": str(e)})

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
    Submits user code, evaluates correctness, updates score, and moves to the next question.
    """
    if request.method != "POST":
        return redirect("editor")

    code = request.POST.get("code")
    if not code:
        return redirect("editor")

    # Retrieve all questions (ordered by ID) and get the current question index.
    questions = list(Questions.objects.all().order_by('id'))
    total_questions = len(questions)
    current_index = request.session.get("question_index", 0)
    print(current_index)

    if total_questions == 0:
        return redirect("editor")

    current_question = questions[current_index]
    correct = False

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            compile_process = compile_java_file(code, "Main.java", temp_dir)
            if compile_process.returncode == 0:
                if current_question.question_type == "IO":
                    correct = all(
                        execute_java_file("Main", temp_dir, input_data=test.test_input).strip()
                        == test.expected_output.strip()
                        for test in current_question.test_cases.all()
                    )
                else:
                    output = execute_java_file("CountPositiveRunner", temp_dir)
                    correct = "Actual: 6" in output
    except Exception as e:
        print("Error processing code:", e)

    # Debugging output
    print(f"Before updating session: question_index={current_index}, correct={correct}")

    if correct:
        request.session["correct_count"] = request.session.get("correct_count", 0) + 1

    # Move to the next question
    new_index = current_index + 1
    print(new_index)
    if new_index >= total_questions:
        request.session["question_index"] = 0  # Reset to first question
    else:
        request.session["question_index"] = new_index

    print(f"After updating session: question_index={request.session['question_index']}")

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
