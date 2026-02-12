import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import secrets
from datetime import datetime
from pathlib import Path
from sqlite3 import IntegrityError

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout, get_user_model
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView
from django.utils.timezone import make_aware
from django.views.decorators.cache import never_cache, cache_control
from django.views.decorators.http import require_POST

from CodeEditor import settings
from decorators import *
from editor.models import ParticipantProfile, Questions, Submission, AITelemetry
from editor.views import compile_java_file, execute_java_file, compile_java_sources

signer = TimestampSigner(salt="pre-survey-v1")

User = get_user_model()



def _difficulty_label(question) -> str:
    """Return a human-friendly difficulty label if the field exists."""
    # If you implement difficulty as a choices field, Django provides get_difficulty_display()
    getter = getattr(question, "get_difficulty_display", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            pass
    # Fallback to raw attribute (or empty string if not present yet)
    return str(getattr(question, "difficulty", "") or "")


def get_attempt_question_lists(user):
    """
    Returns per-attempt lists of which questions were correct/wrong.
    Each item includes question id, name, and difficulty (if available).
    """
    subs = (Submission.objects
            .filter(user=user, attempt_no__in=(1, 2))
            .select_related("question"))

    def pack(qs):
        out = []
        for s in qs:
            q = s.question
            out.append({
                "question_id": q.id,
                "question_name": q.question_name,
                "difficulty": _difficulty_label(q),
                "is_correct": bool(s.is_correct),
            })
        return out

    return {
        "attempt1": {
            "correct": pack(subs.filter(attempt_no=1, is_correct=True)),
            "wrong":   pack(subs.filter(attempt_no=1, is_correct=False)),
        },
        "attempt2": {
            "correct": pack(subs.filter(attempt_no=2, is_correct=True)),
            "wrong":   pack(subs.filter(attempt_no=2, is_correct=False)),
        },
    }


def get_difficulty_summary(user, attempt_no: int):
    """
    Returns grouped counts by (difficulty, is_correct) for the given attempt.
    Works once Questions.difficulty is implemented; otherwise difficulty will be ''.
    """
    # values('question__difficulty') will fail only if the field doesn't exist at all
    # so we guard by checking attribute on the model class.
    if not hasattr(Questions, "difficulty"):
        return []

    return list(
        (Submission.objects
            .filter(user=user, attempt_no=attempt_no)
            .values("question__difficulty", "is_correct")
            .annotate(n=Count("id"))
            .order_by("question__difficulty", "is_correct"))
    )


def get_improved_question_ids(user):
    """Question IDs that were wrong on attempt 1 and correct on attempt 2."""
    s1 = {s.question_id: s.is_correct
          for s in Submission.objects.filter(user=user, attempt_no=1)}
    s2 = {s.question_id: s.is_correct
          for s in Submission.objects.filter(user=user, attempt_no=2)}
    return [qid for qid, ok1 in s1.items() if (ok1 is False and s2.get(qid) is True)]


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
@guard_editor
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

    # Per-question outcome tracking (by attempt and (optionally) by difficulty)
    attempt_lists = get_attempt_question_lists(request.user)
    improved_qids = get_improved_question_ids(request.user)

    # Grouped summaries by difficulty (once you add Questions.difficulty)
    attempt1_difficulty_summary = get_difficulty_summary(request.user, 1)
    attempt2_difficulty_summary = get_difficulty_summary(request.user, 2)

    resp = render(request, "control_app/editor.html", {
        "questions": questions,
        "is_control": is_control,
        "is_experimental": is_experimental,
        "redo_mode": redo_mode,
        "show_ai": show_ai,
        "control_pass": control_pass,
        "first_correct": first_correct,
        "second_correct": second_correct,

        # Detailed attempt breakdowns (for UI/debug/research export)
        "attempt_lists": attempt_lists,
        "improved_qids": improved_qids,
        "attempt1_difficulty_summary": attempt1_difficulty_summary,
        "attempt2_difficulty_summary": attempt2_difficulty_summary,

        "attempt_no": control_pass,
        # if you still want to show their cumulative profile stats:
        "first_score": profile.first_attempt_correct,
        "control_failed": profile.first_attempt_incorrect,
    })
    resp["Cross-Origin-Opener-Policy"] = "same-origin"
    resp["Cross-Origin-Embedder-Policy"] = "require-corp"

    return resp



@login_required
@require_POST
def submit_all(request):
    """
    Handles *all* question submissions in one POST.
    Records a Submission per question (including timing), updates profile counters,
    then returns JSON with the next URL to redirect to.

    Accepts either:
      1) form-encoded payload:
            question_id=<id>&code=<code>&time_spent_ms=<ms>  (repeated for each question)
      2) JSON payload:
            {"submissions":[{"question_id":1,"code":"...","time_spent_ms":1234}, ...]}

    Notes:
    - attempt_no is derived from the server-side session (control_pass) to prevent tampering.
    - counters are recomputed from Submission rows to remain idempotent (no double-counting on re-submit).
    - time_spent_ms is treated as client-reported "active" time on that question for that attempt.
    """
    # --- Parse payload (supports form-encoded and JSON) ---
    if request.content_type and request.content_type.startswith("application/json"):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

        submissions = payload.get("submissions") or []
        question_ids = [str(s.get("question_id", "")).strip() for s in submissions]
        codes = [str(s.get("code", "")) for s in submissions]
        time_spent_raw = [s.get("time_spent_ms", 0) for s in submissions]
    else:
        question_ids = request.POST.getlist("question_id")
        codes = request.POST.getlist("code")
        time_spent_raw = request.POST.getlist("time_spent_ms")

    if len(question_ids) != len(codes):
        return JsonResponse(
            {"error": f"Mismatched payload: received {len(question_ids)} question_ids but {len(codes)} code entries."},
            status=400
        )

    # Normalize/validate qids
    try:
        qids_int = [int(qid) for qid in question_ids]
    except Exception:
        return JsonResponse({"error": "Invalid question_id list."}, status=400)

    # Normalize timing list (pad/trim to match qids)
    def _parse_ms(v):
        try:
            ms = int(float(v))
        except Exception:
            ms = 0
        if ms < 0:
            ms = 0
        # Safety cap: 24 hours per question (prevents obvious bad data / tampering)
        cap = 24 * 60 * 60 * 1000
        if ms > cap:
            ms = cap
        return ms

    time_ms = [_parse_ms(v) for v in time_spent_raw]
    if len(time_ms) < len(qids_int):
        time_ms.extend([0] * (len(qids_int) - len(time_ms)))
    elif len(time_ms) > len(qids_int):
        time_ms = time_ms[:len(qids_int)]

    profile = request.user.participantprofile
    is_ctrl = (profile.group == ParticipantProfile.CONTROL)

    # First-pass or second-pass?
    control_pass = request.session.get("control_pass", 1)

    # Prevent double-counting if the user submits twice (reload/back/etc.)
    Submission.objects.filter(
        user=request.user,
        attempt_no=control_pass,
        question_id__in=qids_int,
    ).delete()

    wrong_ids = []

    # Loop through each pair
    for qid, code, spent_ms in zip(qids_int, codes, time_ms):
        question = get_object_or_404(Questions, pk=qid)

        # Compile & run
        is_correct = False
        harness = (question.harness_code or "").strip()
        if not harness:
            return JsonResponse(
                {"error": f"Server configuration error: harness_code missing for question {qid}."},
                status=500
            )

        try:
            with tempfile.TemporaryDirectory() as tmp:
                compile_proc = compile_java_sources(tmp, {
                    "Solution.java": code,
                    "Main.java": harness,
                })

                if compile_proc.returncode == 0:
                    if question.question_type == "IO":
                        is_correct = all(
                            execute_java_file("Main", tmp, input_data=tc.test_input).strip()
                            == tc.expected_output.strip()
                            for tc in question.test_cases.all()
                        )
                else:
                    is_correct = False
        except Exception as e:
            print("submit_all grading error:", repr(e))
            is_correct = False

        # Record submission (includes timing)
        Submission.objects.create(
            user=request.user,
            question=question,
            attempt_no=control_pass,
            used_ai=(is_ctrl and control_pass == 2),
            is_correct=is_correct,
            time_spent_ms=spent_ms,
        )

        if control_pass == 1 and (not is_correct):
            wrong_ids.append(question.id)

    # Recompute counters from DB (idempotent + also works for pass 2)
    profile.first_attempt_correct = Submission.objects.filter(
        user=request.user, attempt_no=1, is_correct=True
    ).count()
    profile.first_attempt_incorrect = Submission.objects.filter(
        user=request.user, attempt_no=1, is_correct=False
    ).count()

    # Your schema has second_attempt_correct; update it from attempt_no=2 Submissions
    if hasattr(profile, "second_attempt_correct"):
        profile.second_attempt_correct = Submission.objects.filter(
            user=request.user, attempt_no=2, is_correct=True
        ).count()

    # If you add a second_attempt_incorrect field later, this will start populating it automatically
    if hasattr(profile, "second_attempt_incorrect"):
        profile.second_attempt_incorrect = Submission.objects.filter(
            user=request.user, attempt_no=2, is_correct=False
        ).count()

    profile.save()

    # Decide where to go
    if is_ctrl:
        if control_pass == 1:
            # Prepare second pass
            request.session["redo_questions"] = wrong_ids
            request.session["control_pass"] = 2
            request.session.modified = True

            if not wrong_ids:
                # Everyone correct → thank you
                return JsonResponse({
                    "next": "thank-you",
                    "redirect_url": reverse("thank-you")
                })
            else:
                # Some wrong → go back to editor for only wrong ones
                return JsonResponse({
                    "next": "second-pass",
                    "redirect_url": reverse("control_app:editor")
                })

        # Pass 2 always goes to post assessment
        profile.both_ai_and_non_ai_portion_of_code_assessment_completed = True
        profile.save()
        return JsonResponse({
            "status": "redirect",
            "redirect_url": reverse("post-assessment")
        })

    # Non-control fallback (or unexpected group mapping)
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

    harness = (
            question.harness_code or "").strip()  # your model includes this field :contentReference[oaicite:2]{index=2}
    if not harness:
        return JsonResponse(
            {"error": "Server configuration error: harness_code (Main.java) is missing for this question."}, status=500)

    test_cases = question.test_cases.all()
    results = []

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1) Compile Main.java and Solution.java
            cp = compile_java_sources(temp_dir, {
                "Solution.java": code,
                "Main.java": harness,
            })
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

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"results": results})


@login_required(login_url='login')
@guard_pre
@cache_control(no_store=True, no_cache=True, must_revalidate=True, max_age=0, private=True)
def pre_assessment_questionnaire(request):
    profile = request.user.participantprofile
    token = secrets.token_urlsafe(16)
    profile.pre_assessment_token = token
    profile.save(update_fields=["pre_assessment_token"])

    qualtrics_link = settings.QUALTRICS_PREASSESSMENT_LINK  # e.g. "https://yourdcid.qualtrics.com"
    state = signer.sign(token)  # Put this on the Qualtrics link
    return redirect(f"{qualtrics_link}?uid={request.user.id}&state={state}")


@login_required(login_url='login')
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


@guard_post
@cache_control(no_store=True, no_cache=True, must_revalidate=True, max_age=0, private=True)
def post_assessment_questionnaire(request):
    profile = request.user.participantprofile

    # prerequisites (already enforced these elsewhere)
    if not profile.pre_assessment_completed or not profile.both_ai_and_non_ai_portion_of_code_assessment_completed:
        return redirect("editor")

    # mark “in progress”
    if not profile.post_assessment_started:
        profile.post_assessment_started = True
        profile.save(update_fields=["post_assessment_started"])

    token = secrets.token_urlsafe(16)
    profile.post_assessment_token = token
    profile.save(update_fields=["post_assessment_token"])

    state = signer.sign(token)
    qualtrics_link = settings.QUALTRICS_POSTASSESSMENT_LINK  # Qualtrics post-assessment URL

    # Send uid and state, so you can pipe them back on redirect
    return redirect(f"{qualtrics_link}?uid={request.user.id}&state={state}")


@login_required(login_url='login')
@guard_post
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


@login_required
@require_POST
def ai_telemetry(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    # Minimal required field
    event = data.get("event")
    if event not in {"ai_tab_open", "ai_prompt", "ai_reply", "paste", "vis_hide", "vis_show"}:
        return HttpResponseBadRequest("Unknown event")

    # Optional numeric fields
    attempt_no = data.get("attempt_no")
    question_id = data.get("question_id")
    model_id = data.get("model_id") or ""
    prompt = (data.get("prompt") or "")[:4000]
    reply = (data.get("reply") or "")[:4000]
    paste_chars = data.get("paste_chars")
    client_ts = data.get("client_ts")

    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest() if prompt else ""
    reply_hash = hashlib.sha256(reply.encode()).hexdigest() if reply else ""

    ct = None
    if client_ts:
        try:
            ct = make_aware(datetime.datetime.fromisoformat(client_ts))
        except Exception:
            ct = None

    AITelemetry.objects.create(
        user=request.user,
        attempt_no=attempt_no,
        event=event,
        prompt=prompt or None,
        reply_chars=len(reply) or None,
    )
    return JsonResponse({"ok": True})


def thank_you(request):
    raw = (request.GET.get("entered_raffle") or "").strip().lower()
    entered_raffle = raw in {"1", "true", "yes", "y", "on"}
    return render(request, "thank_you.html", {"entered_raffle": entered_raffle})


def logout_view(request):
    """Logout user and redirect to login page."""
    logout(request)
    return redirect('login')
