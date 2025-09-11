import os
import subprocess
import tempfile

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView

from editor.models import ParticipantProfile, Questions, Submission
from editor.forms import QuestionsForm, TestCaseFormSet
from editor.views import editor as core_editor, compile_java_file, execute_java_file


def register_control(request):
    """
    A single page that offers both Login and Register tabs.
    We auto‐generate the username as the new User.pk.
    """
    # Prepare an empty login form for either GET or POST
    login_form = AuthenticationForm()

    if request.method == "POST":
        # Grab the two password fields directly
        pwd1 = request.POST.get("password1")
        pwd2 = request.POST.get("password2")

        # If passwords are empty or don’t match, redisplay Register tab with error
        if not pwd1 or pwd1 != pwd2:
            return render(request, "control_app/login_register_c.html", {
                "form": login_form,
                "register_error": "Passwords must match and not be empty.",
                # no generated_username → stays on Register tab
            })

        # 1) Create a temporary user, so we get an auto PK
        temp_user = User.objects.create_user(username="temp", password=pwd1)

        # 2) Take its PK, convert to string, overwrite username
        new_username = str(temp_user.id)
        temp_user.username = new_username
        temp_user.save()

        # 3) Assign them to Control group
        profile = temp_user.participantprofile
        profile.group = "C"
        profile.save()

        # 4) Re‐render the SAME page, but now show the success banner + Login tab
        return render(request, "control_app/login_register_c.html", {
            "generated_username": new_username,
            "form": AuthenticationForm(),  # fresh login form
            # we can show a fresh placeholder register form or leave it out
        })

    # GET: just render both blank forms
    return render(request, "control_app/login_register_c.html", {
        "form": login_form,
    })


class ControlLoginView(LoginView):
    template_name = "control_app/login_register_c.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("control_app:editor")

    def get_success_url(self):
        return self.success_url


@login_required
def editor(request):
    profile = request.user.participantprofile
    is_control = (profile.group == ParticipantProfile.CONTROL)
    is_experimental = False
    profile.control_assessment_done_and_ai_used = True
    print(profile.control_assessment_done_and_ai_used)

    # which pass are they on? 1 = first try, 2 = second try
    control_pass = request.session.get("control_pass", 1)
    redo_mode = (control_pass == 2)

    # pick questions
    if control_pass == 1:
        questions = Questions.objects.order_by("id")[:3]
        show_ai = False
    else:
        wrong_ids = request.session.get("redo_questions", [])
        questions = Questions.objects.filter(id__in=wrong_ids).order_by("id")
        show_ai = True

    # how many they got right on pass 1 and pass 2
    first_correct = Submission.objects.filter(
        user=request.user, attempt_no=1, is_correct=True
    ).count()
    second_correct = Submission.objects.filter(
        user=request.user, attempt_no=2, is_correct=True
    ).count()

    return render(request, "control_app/editor.html", {
        "questions": questions,
        "is_control": is_control,
        "is_experimental": is_experimental,
        "redo_mode": redo_mode,
        "show_ai": show_ai,
        "control_pass": control_pass,
        "first_correct": first_correct,
        "second_correct": second_correct,
        # if you still want to show their cumulative profile stats:
        "first_score": profile.first_attempt_correct,
        "control_failed": profile.first_attempt_incorrect,
    })


@login_required
def submit_all(request):
    """
    Handles *all* question submissions in one POST.
    Records a Submission per question, updates profile,
    then returns JSON with the next URL to redirect to.
    """
    question_ids = request.POST.getlist('question_id')
    codes = request.POST.getlist('code')
    print("POSTed QIDs:", question_ids)

    profile = request.user.participantprofile
    is_ctrl = profile.group == ParticipantProfile.CONTROL

    # first‐pass or second‐pass?
    control_pass = request.session.get("control_pass", 1)

    wrong_ids = []
    # loop through each pair
    for qid, code in zip(question_ids, codes):
        q = get_object_or_404(Questions, pk=int(qid))
        # compile & run
        is_correct = False
        try:
            with tempfile.TemporaryDirectory() as tmp:
                cp = compile_java_file(code, "Main.java", tmp)
                if cp.returncode == 0:
                    if q.question_type == "IO":
                        is_correct = all(
                            execute_java_file("Main", tmp, input_data=tc.test_input).strip()
                            == tc.expected_output.strip()
                            for tc in q.test_cases.all()
                        )
                    else:
                        # unit‐test path (CountPositiveRunner)
                        runner_src = "/Users/jaden/PycharmProjects/CodeEditor/java/CountPositiveRunner.java"
                        dst = os.path.join(tmp, "CountPositiveRunner.java")
                        subprocess.run(["cp", runner_src, dst], check=True)
                        cr = subprocess.run(["javac", dst], capture_output=True, text=True)
                        if cr.returncode == 0:
                            out = execute_java_file("CountPositiveRunner", tmp).splitlines()
                            actual = next((l.split("Actual:")[1].strip()
                                           for l in out if l.startswith("Actual:")), None)
                            is_correct = (actual == "6")
        except:
            is_correct = False

        # record submission
        Submission.objects.create(
            user=request.user,
            question=q,
            attempt_no=control_pass,
            used_ai=(is_ctrl and control_pass == 2),
            is_correct=is_correct
        )

        # update profile counters
        if control_pass == 1:
            if is_correct:
                profile.first_attempt_correct += 1
            else:
                profile.first_attempt_incorrect += 1

        if not is_correct and control_pass == 1:
            wrong_ids.append(q.id)

    print(">> received qids:", question_ids)
    print(">> received codes:", len(codes), "items")
    profile.save()

    # now decide where to go
    if is_ctrl:
        if control_pass == 1:
            # prepare second pass
            print(">> wrong_ids going into session:", wrong_ids)
            request.session['redo_questions'] = wrong_ids
            request.session['control_pass'] = 2
            request.session.modified = True

            if not wrong_ids:
                # everyone correct → thank you
                return JsonResponse({
                    "next": "thank-you",
                    "redirect_url": reverse("control_app:thank-you")
                })
            else:
                # some wrong → go back to editor for only wrong ones
                return JsonResponse({
                    "next": "second-pass",
                    "redirect_url": reverse("control_app:editor")
                })

        # pass 2 always goes to thank-you
        # probably assign control_assessment_done_and_ai_used:
        profile.control_assessment_done_and_ai_used = True
        print(profile.control_assessment_done_and_ai_used)
        return JsonResponse({
            "next": "thank-you",
            "redirect_url": reverse("control_app:thank-you")
        })

    # non-control fallback
    return JsonResponse({
        "next": "editor",
        "redirect_url": reverse("control_app:editor")
    })


# @login_required
# def submit_code(request):
#     # 1) Pull form data
#     code = request.POST.get("code", "").strip()
#     qid = request.POST.get("question_id")
#     attempt_no = int(request.POST.get("attempt_no", "1"))
#
#     if not code or not qid:
#         return redirect("control_app:editor")
#
#     # 2) Lookup objects & profile
#     question = get_object_or_404(Questions, pk=int(qid))
#     profile = request.user.participantprofile
#     is_ctrl = (profile.group == ParticipantProfile.CONTROL)
#
#     # 3) Compile & run tests (your existing logic)
#     is_correct = False
#     used_ai = False
#     try:
#         with tempfile.TemporaryDirectory() as tmp:
#             cpp = compile_java_file(code, "Main.java", tmp)
#             if cpp.returncode == 0:
#                 if question.question_type == "IO":
#                     is_correct = all(
#                         execute_java_file("Main", tmp, input_data=tc.test_input).strip()
#                         == tc.expected_output.strip()
#                         for tc in question.test_cases.all()
#                     )
#                 else:
#                     # Unit test runner
#                     runner_src = "/Users/jaden/PycharmProjects/CodeEditor/java/CountPositiveRunner.java"
#                     dest = os.path.join(tmp, "CountPositiveRunner.java")
#                     subprocess.run(["cp", runner_src, dest], check=True)
#                     cr = subprocess.run(["javac", dest], capture_output=True, text=True)
#                     if cr.returncode == 0:
#                         lines = execute_java_file("CountPositiveRunner", tmp).splitlines()
#                         actual = next((l.split("Actual:")[1].strip()
#                                        for l in lines if l.startswith("Actual:")), None)
#                         is_correct = (actual == "6")
#     except Exception:
#         is_correct = False
#
#     # 4) Did they use AI?
#
#     if is_ctrl and attempt_no == 2:
#         used_ai = True
#
#     # 5) Record the submission
#     Submission.objects.create(
#         user=request.user,
#         question=question,
#         attempt_no=attempt_no,
#         used_ai=used_ai,
#         is_correct=is_correct
#     )
#
#     # 6) Update profile counters
#     if attempt_no == 1:
#         if is_correct:
#             profile.first_attempt_correct += 1
#         else:
#             profile.first_attempt_incorrect += 1
#     profile.save()
#
#     # 7) Control-group two-pass logic
#     if is_ctrl:
#         sess = request.session
#         control_pass = sess.get("control_pass", 1)
#         wrong_questions = sess.get("redo_questions", [])
#
#         if control_pass == 1:
#             # first pass → collect any wrongs
#             if not is_correct:
#                 wrong_questions.append(question.id)
#             sess["redo_questions"] = wrong_questions
#             sess["control_pass"] = 2
#             sess.modified = True
#
#             # if they got all three correct → thank you
#             if len(wrong_questions) == 0:
#                 return redirect("control_app:thank_you")
#             # otherwise back to editor for second try
#             return redirect(reverse("control_app:editor"))
#
#         # second pass always goes to thank you
#         return redirect("control_app:thank_you")
#
#     # 9) Default: next question
#     return redirect("control_app:editor")


@login_required
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


def thank_you(request):
    return render(request, "control_app/thank_you.html")


def logout_view(request):
    """Logout user and redirect to login page."""
    logout(request)
    return redirect('control_app:login')
