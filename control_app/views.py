import os
import subprocess
import tempfile
import secrets
from datetime import datetime
from sqlite3 import IntegrityError

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.db import transaction
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout, get_user_model
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView
from django.views.decorators.cache import never_cache, cache_control

from CodeEditor import settings
from decorators import require_pre_assessment_completed, require_ready_for_post_assessment_questionnaire
from editor.models import ParticipantProfile, Questions, Submission
from editor.views import compile_java_file, execute_java_file

signer = TimestampSigner(salt="pre-survey-v1")

User = get_user_model()


def register_control(request):
    """
    Do NOT assign study group here. Group is assigned after pre-survey completes.
    """
    login_form = AuthenticationForm(request)

    if request.method == "POST":
        pwd1 = request.POST.get("password1")
        pwd2 = request.POST.get("password2")

        if not pwd1 or pwd1 != pwd2:
            return render(request, "login_register.html", {
                "form": login_form,
                "register_error": "Passwords must match and not be empty.",
            })

        try:
            with transaction.atomic():
                # 1) Create with a unique placeholder to avoid 'temp' collisions
                placeholder = f"_tmp_{secrets.token_urlsafe(8)}"
                user = User.objects.create_user(username=placeholder, password=pwd1)

                # 2) Rename to the numeric PK string (unique by definition)
                user.username = str(user.pk)
                user.save(update_fields=["username"])

                # 3) Ensure a ParticipantProfile exists (if not created via signal)
                # from .models import ParticipantProfile
                # ParticipantProfile.objects.get_or_create(user=user)

        except IntegrityError:
            # Extremely rare; try again with a new placeholder
            return render(request, "login_register.html", {
                "form": login_form,
                "register_error": "Please try again.",
            })

        # after user is created and renamed:
        # login(request, user)
        # return redirect("control_app:pre_assessment_questionnaire")

        # 4) Show success banner + keep them on the same page to log in
        return render(request, "login_register.html", {
            "generated_username": user.username,
            "form": AuthenticationForm(request),  # fresh login form
        })

    # GET
    return render(request, "login_register.html", {"form": login_form})


class ControlLoginView(LoginView):
    template_name = "login_register.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("control_app:editor")

    def get_success_url(self):
        return self.success_url


@login_required(login_url='login')
@require_pre_assessment_completed
@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True, max_age=0, private=True)
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

    resp = render(request, "control_app/editor.html", {
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
    resp["Cross-Origin-Opener-Policy"] = "same-origin"
    resp["Cross-Origin-Embedder-Policy"] = "require-corp"

    return resp


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
                    "redirect_url": reverse("thank-you")
                })
            else:
                # some wrong → go back to editor for only wrong ones
                return JsonResponse({
                    "next": "second-pass",
                    "redirect_url": reverse("control_app:editor")
                })

        # pass 2 always goes to post assessment
        profile.both_ai_and_non_ai_portion_of_code_assessment_completed = True
        profile.save()
        return JsonResponse({
            "status": "redirect",
            "redirect_url": reverse("post-assessment")
        })

    # non-control fallback
    return HttpResponse("An unexpected error has occurred")


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


@login_required
def pre_assessment_questionnaire(request):
    profile = request.user.participantprofile
    token = secrets.token_urlsafe(16)
    profile.pre_assessment_token = token
    profile.save(update_fields=["pre_assessment_token"])

    qualtrics_link = settings.QUALTRICS_PREASSESSMENT_LINK  # e.g. "https://yourdcid.qualtrics.com"
    state = signer.sign(token)  # Put this on the Qualtrics link
    return redirect(f"{qualtrics_link}?uid={request.user.id}&state={state}")


@login_required
@transaction.atomic
def pre_assessment_complete(request):
    user = request.user
    profile = (user.participantprofile.__class__.objects
               .select_for_update().get(pk=user.participantprofile.pk))

    # If already completed, be idempotent: just go to the editor for their group.
    if profile.pre_assessment_completed:
        if profile.group == "C":
            return redirect("control_app:editor")
        if profile.group == "E":
            return redirect("experimental_app:editor")
        # If no group yet, assign now and continue.

    # --- 1) Read and verify inputs ---
    state = request.GET.get("state")
    response_id = request.GET.get("responseId")  # optional but useful
    q_uid = request.GET.get("uid")  # optional cross-check

    if not state:
        return HttpResponseBadRequest("Missing state")

    # Require that Qualtrics returned within (e.g.) 2 hours
    try:
        token = signer.unsign(state, max_age=7200)  # seconds
    except SignatureExpired:
        return HttpResponseForbidden("State expired")
    except BadSignature:
        return HttpResponseForbidden("Invalid state")

    # Token must match what we issued to this logged-in user
    if token != (profile.pre_assessment_token or ""):
        return HttpResponseForbidden("Token mismatch")

    # Optional: uid mismatch warning (doesn't control which profile we write)
    if q_uid and str(q_uid) != str(user.pk):
        return HttpResponseForbidden("UID mismatch")

    # --- 2) Mark completion & clear token ---
    profile.pre_assessment_completed = True
    profile.pre_assessment_response_id = response_id or ""
    profile.pre_assessment_token = ""  # one-time use
    profile.pre_assessment_completed_at = datetime.now()  # add this field if you like
    profile.save(update_fields=[
        "pre_assessment_completed", "pre_assessment_response_id",
        "pre_assessment_token", "pre_assessment_completed_at"
    ])

    # --- 3) Assign group AFTER verified completion ---
    if not profile.group:
        from randomize_block_permutation import assign_group
        assign_group(user)  # respects your 130/130 caps
        profile.refresh_from_db(fields=["group"])

    # --- 4) Redirect to the correct editor ---
    if profile.group == "C":
        return redirect("control_app:editor")
    if profile.group == "E":
        return redirect("experimental_app:editor")
    return HttpResponseBadRequest("Couldn't find your group")


@require_ready_for_post_assessment_questionnaire
def post_assessment_questionnaire(request):
    profile = request.user.participantprofile
    token = secrets.token_urlsafe(16)
    profile.post_assessment_token = token
    profile.save(update_fields=["post_assessment_token"])

    state = signer.sign(token)
    qualtrics_link = settings.QUALTRICS_POSTASSESSMENT_LINK  # Qualtrics post-assessment URL

    # Send uid and state, so you can pipe them back on redirect
    return redirect(f"{qualtrics_link}?uid={request.user.id}&state={state}")


@login_required
@transaction.atomic
def post_assessment_complete(request):
    profile = (request.user.participantprofile.__class__.objects
               .select_for_update()
               .get(pk=request.user.participantprofile.pk))

    # Must still meet prerequisites (defense-in-depth)
    if not profile.pre_assessment_completed or not profile.both_ai_and_non_ai_portion_of_code_assessment_completed:
        return HttpResponseForbidden("Prerequisites not met")

    # Already done? be idempotent
    if profile.post_assessment_completed:
        # send to your final screen / thanks
        return redirect("thank_you")

    state = request.GET.get("state")
    response_id = request.GET.get("responseId") or request.GET.get("Q_R")  # Qualtrics sometimes uses Q_R
    q_uid = request.GET.get("uid")

    if not state:
        return HttpResponseBadRequest("Missing state")

    try:
        token = signer.unsign(state, max_age=7200)  # 2 hours
    except SignatureExpired:
        return HttpResponseForbidden("State expired")
    except BadSignature:
        return HttpResponseForbidden("Invalid state")

    if token != (profile.post_assessment_token or ""):
        return HttpResponseForbidden("Token mismatch")

    # (Optional) sanity check – never use q_uid to choose the account
    if q_uid and str(q_uid) != str(request.user.pk):
        return HttpResponseForbidden("UID mismatch")

    # Mark complete and clear token
    profile.post_assessment_completed = True
    profile.post_assessment_response_id = response_id or ""
    profile.post_assessment_token = ""
    profile.post_assessment_completed_at = datetime.now()
    profile.save(update_fields=[
        "post_assessment_completed",
        "post_assessment_response_id",
        "post_assessment_token",
        "post_assessment_completed_at",
    ])

    # in post_assessment_complete (after verifying state/token and marking completion):
    request.user.is_active = False
    request.user.save(update_fields=["is_active"])
    logout(request)  # end the current session

    return redirect("thank-you")  # or wherever you end


def thank_you(request):
    return render(request, "thank_you.html")


class ControlLoginView(LoginView):
    template_name = "login_register.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("pre-assessment")

    def get_success_url(self):
        return self.success_url


def logout_view(request):
    """Logout user and redirect to login page."""
    logout(request)
    return redirect('login')
