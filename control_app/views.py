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
from django.utils import timezone
from django.views.decorators.cache import never_cache, cache_control
from django.views.decorators.http import require_POST
from datetime import timedelta

from CodeEditor import settings
from decorators import *
from editor.models import ParticipantProfile, Questions, Submission, AITelemetry
from editor.views import compile_java_file, execute_java_file, compile_java_sources, grade_io_question

signer = TimestampSigner(salt="pre-survey-v1")

User = get_user_model()

# ---- Coding time window (study design: 35 min coding + ~5 min surveys) ----
# ---- Coding time windows (per attempt) ----
# Example split: 23:00 + 12:00
CODING_LIMITS_BY_PASS = {
    1: 23 * 60,  # Attempt 1 (23 minutes)
    2: 12 * 60,  # Attempt 2 (12 minutes)
}

# You can change these later, e.g.:
# 1: 22 * 60 + 30,
# 2: 12 * 60 + 30,

CODING_WINDOW_START_KEY = "coding_window_started_at"
CODING_WINDOW_DEADLINE_KEY = "coding_window_deadline_at"
CODING_WINDOW_PASS_KEY = "coding_window_pass_no"


def _coding_limit_for_pass(pass_no: int) -> int:
    try:
        p = int(pass_no)
    except Exception:
        p = 1
    return int(CODING_LIMITS_BY_PASS.get(p, CODING_LIMITS_BY_PASS[1]))


def _ensure_coding_window(request, pass_no: int):
    """
    Create/reuse a coding window for the CURRENT pass only.
    - Reloading the same pass reuses the same deadline.
    - Switching pass 1 -> pass 2 creates a NEW window with pass 2's duration.
    """
    now = timezone.now()

    try:
        requested_pass = int(pass_no or 1)
    except Exception:
        requested_pass = 1

    started_iso = request.session.get(CODING_WINDOW_START_KEY)
    deadline_iso = request.session.get(CODING_WINDOW_DEADLINE_KEY)
    stored_pass = request.session.get(CODING_WINDOW_PASS_KEY)

    # Reuse only if the stored window belongs to the same pass
    if started_iso and deadline_iso and str(stored_pass) == str(requested_pass):
        try:
            started_at = timezone.datetime.fromisoformat(started_iso)
            deadline_at = timezone.datetime.fromisoformat(deadline_iso)

            if timezone.is_naive(started_at):
                started_at = timezone.make_aware(started_at, timezone.get_current_timezone())
            if timezone.is_naive(deadline_at):
                deadline_at = timezone.make_aware(deadline_at, timezone.get_current_timezone())

            return started_at, deadline_at
        except Exception:
            pass  # fall through and recreate

    # New window for this pass
    limit_seconds = _coding_limit_for_pass(requested_pass)
    started_at = now
    deadline_at = now + timedelta(seconds=limit_seconds)

    request.session[CODING_WINDOW_START_KEY] = started_at.isoformat()
    request.session[CODING_WINDOW_DEADLINE_KEY] = deadline_at.isoformat()
    request.session[CODING_WINDOW_PASS_KEY] = requested_pass
    request.session.modified = True

    return started_at, deadline_at


def _get_coding_window(request, pass_no=None):
    """
    Returns (started_at, deadline_at) for the current coding phase.
    If pass_no is omitted, infer it from the session.
    """
    if pass_no is None:
        pass_no = request.session.get("control_pass", 1)
    return _ensure_coding_window(request, pass_no)

def _clear_coding_window(request):
    request.session.pop(CODING_WINDOW_START_KEY, None)
    request.session.pop(CODING_WINDOW_DEADLINE_KEY, None)
    request.session.pop(CODING_WINDOW_PASS_KEY, None)
    request.session.modified = True


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
            "wrong": pack(subs.filter(attempt_no=1, is_correct=False)),
        },
        "attempt2": {
            "correct": pack(subs.filter(attempt_no=2, is_correct=True)),
            "wrong": pack(subs.filter(attempt_no=2, is_correct=False)),
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

    # Safety: keep users in their assigned app
    if profile.group != ParticipantProfile.CONTROL:
        return redirect(editor_url_for(request.user))

    is_control = (profile.group == ParticipantProfile.CONTROL)
    is_experimental = False

    # which pass are they on? 1 = first try, 2 = second try
    control_pass = request.session.get("control_pass", 1)

    # If you track whether AI was ever shown/used in control, only set it when pass 2 is active
    if hasattr(profile, "control_assessment_done_and_ai_used"):
        profile.control_assessment_done_and_ai_used = (control_pass == 2)
        try:
            profile.save(update_fields=["control_assessment_done_and_ai_used"])
        except Exception:
            # field might not be DB-backed in some environments; ignore
            pass

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

    coding_started_at, coding_deadline_at = _ensure_coding_window(request, control_pass)
    now = timezone.now()
    remaining_seconds = max(0, int((coding_deadline_at - now).total_seconds()))

    resp = render(request, "control_app/editor.html", {
        "questions": questions,
        "is_control": is_control,
        "is_experimental": is_experimental,
        "redo_mode": redo_mode,
        "show_ai": show_ai,
        "control_pass": control_pass,
        "first_correct": first_correct,
        "second_correct": second_correct,

        "coding_deadline_epoch_ms": int(coding_deadline_at.timestamp() * 1000),
        "coding_remaining_seconds": remaining_seconds,
        "coding_limit_seconds": _coding_limit_for_pass(control_pass),

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
        cap = 24 * 60 * 60 * 1000  # 24h safety cap
        if ms > cap:
            ms = cap
        return ms

    time_ms = [_parse_ms(v) for v in time_spent_raw]
    if len(time_ms) < len(qids_int):
        time_ms.extend([0] * (len(qids_int) - len(time_ms)))
    elif len(time_ms) > len(qids_int):
        time_ms = time_ms[:len(qids_int)]

    profile = request.user.participantprofile

    # Safety: this submit_all is for control users only
    if profile.group != ParticipantProfile.CONTROL:
        return JsonResponse({"error": "Not authorized. For control submissions onluy."}, status=403)

    # First-pass or second-pass?
    control_pass = request.session.get("control_pass", 1)

    if control_pass == 2:
        allowed = set(int(x) for x in (request.session.get("redo_questions", []) or []))

        # Filter payload to only allowed qids
        filtered = [(qid, code, ms) for (qid, code, ms) in zip(qids_int, codes, time_ms) if qid in allowed]

        # Option A (recommended): silently ignore any extra qids
        qids_int = [t[0] for t in filtered]
        codes = [t[1] for t in filtered]
        time_ms = [t[2] for t in filtered]

    wrong_ids = []

    for qid, code, spent_ms in zip(qids_int, codes, time_ms):
        question = get_object_or_404(Questions, pk=qid)

        results = []
        compile_err = ""
        runtime_err = ""

        # --- Grade ---
        try:
            if question.question_type == "IO":
                results, compile_err, runtime_err = grade_io_question(question, code)
            else:
                # If you later add UNIT grading, plug it in here.
                compile_err = "UNIT grading not implemented."
                results = []
        except Exception as e:
            # Treat unexpected exceptions like compile/grade failures, but still SAVE a row.
            compile_err = (compile_err + "\n" + repr(e)).strip() if compile_err else repr(e)
            results = []

        # --- Compute stats to save ---
        if results:
            total = len(results)
            passed_count = sum(1 for r in results if r.get("passed"))
            failed_ids = [
                r.get("test_case_id")
                for r in results
                if not r.get("passed") and r.get("test_case_id") is not None
            ]
        else:
            # If compile failed / no results returned, treat all testcases as failed (stable IDs).
            total = getattr(question, "test_cases", None).count() if hasattr(question, "test_cases") else 0
            passed_count = 0
            failed_ids = list(question.test_cases.values_list("id", flat=True)) if total else []

        is_correct = (total > 0 and passed_count == total and not compile_err and not runtime_err)

        # IMPORTANT: for control group, AI is only available on pass 2 (your editor sets show_ai=True on pass 2)
        used_ai_flag = (control_pass == 2)

        Submission.objects.update_or_create(
            user=request.user,
            question=question,
            attempt_no=control_pass,
            defaults={
                "used_ai": used_ai_flag,
                "is_correct": is_correct,
                "time_spent_ms": spent_ms,
                "code": code,
                "total_test_cases": total,
                "passed_test_cases": passed_count,
                "failed_testcase_ids": failed_ids,
                "compile_error": compile_err or "",
                "runtime_error": runtime_err or "",
            }
        )

        if control_pass == 1 and (not is_correct):
            wrong_ids.append(question.id)

    # --- Recompute counters from DB (idempotent) ---
    profile.first_attempt_correct = Submission.objects.filter(
        user=request.user, attempt_no=1, is_correct=True
    ).count()
    profile.first_attempt_incorrect = Submission.objects.filter(
        user=request.user, attempt_no=1, is_correct=False
    ).count()

    if hasattr(profile, "second_attempt_correct"):
        profile.second_attempt_correct = Submission.objects.filter(
            user=request.user, attempt_no=2, is_correct=True
        ).count()

    if hasattr(profile, "second_attempt_incorrect"):
        profile.second_attempt_incorrect = Submission.objects.filter(
            user=request.user, attempt_no=2, is_correct=False
        ).count()

    profile.save()

    # --- Redirect logic (keep your existing behavior) ---
    if control_pass == 1:
        if not wrong_ids:
            profile.control_all_correct = True
            profile.save(update_fields=["control_all_correct"])

            request.session.pop("redo_questions", None)
            request.session.pop("control_pass", None)
            request.session.modified = True
            _clear_coding_window(request)

            return JsonResponse({"next": "raffle-entry", "redirect_url": reverse("raffle-entry")})

        request.session["redo_questions"] = wrong_ids
        request.session["control_pass"] = 2
        request.session.modified = True
        _clear_coding_window(request)

        return JsonResponse({"next": "second-pass", "redirect_url": reverse("control_app:editor")})

    # Pass 2 goes to post assessment
    profile.both_ai_and_non_ai_portion_of_code_assessment_completed = True
    profile.save(update_fields=["both_ai_and_non_ai_portion_of_code_assessment_completed"])

    request.session.pop("redo_questions", None)
    request.session.pop("control_pass", None)
    request.session.modified = True

    return JsonResponse({"status": "redirect", "redirect_url": reverse("post-assessment")})


@login_required(login_url="login")
@require_POST
def run_code(request):
    code = (request.POST.get("code") or "").strip()
    qid = request.POST.get("question_id")

    control_pass = request.session.get("control_pass", 1)
    _, coding_deadline_at = _get_coding_window(request, control_pass)
    if timezone.now() >= coding_deadline_at:
        return JsonResponse({
            "error": "Coding time is up. Please submit your work.",
            "deadline_reached": True
        }, status=403)

    if not code:
        return JsonResponse({"error": "No code provided."}, status=400)
    if not qid:
        return JsonResponse({"error": "No question_id provided."}, status=400)

    try:
        question = Questions.objects.get(pk=int(qid))
    except (Questions.DoesNotExist, ValueError):
        return JsonResponse({"error": "Invalid question_id."}, status=400)

    if question.question_type != "IO":
        return JsonResponse({"error": "UNIT grading not implemented yet."}, status=400)

    try:
        results, compile_err, runtime_err = grade_io_question(question, code)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed"))
    failed_ids = [r["test_case_id"] for r in results if not r.get("passed")]

    payload = {
        "results": results,
        "summary": {
            "total": total,
            "passed": passed_count,
            "failed_testcase_ids": failed_ids,
            "compile_error": compile_err or "",
            "runtime_error": runtime_err or "",
        }
    }

    # Only set top-level "error" when you actually want the UI error path to trigger.
    # Compile errors should definitely trigger it.
    if compile_err:
        payload["error"] = compile_err

        # Optional: you can return 200 here to keep fetch+json parsing simple
        return JsonResponse(payload, status=200)

    # Optional: if you want runtime errors to also show in the "compiler output" box,
    # you can uncomment this. But note: if your JS returns early on data.error,
    # it will stop rendering testcase details.
    #
    # if runtime_err:
    #     payload["error"] = runtime_err

    return JsonResponse(payload, status=200)


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


@login_required(login_url='login')
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
        # If they've already completed the post, send them to raffle (or thanks if raffle is done)
        if profile.raffle_page_completed:
            return redirect("thank-you")
        return redirect("raffle-entry")

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

    return redirect("raffle-entry")


@login_required(login_url='login')
@guard_raffle
@transaction.atomic
def raffle_entry(request):
    profile = request.user.participantprofile

    token = secrets.token_urlsafe(16)
    profile.raffle_token = token
    profile.save(update_fields=["raffle_token"])

    state = signer.sign(token)
    qualtrics_link = settings.QUALTRICS_RAFFLE_LINK  # Qualtrics raffle link

    # Send uid and state, so you can pipe them back on redirect
    return redirect(f"{qualtrics_link}?uid={request.user.id}&state={state}")


@login_required(login_url='login')
@guard_raffle
@transaction.atomic
def raffle_entry_complete(request):
    profile = (request.user.participantprofile.__class__.objects
               .select_for_update()
               .get(pk=request.user.participantprofile.pk))

    # Already done? be idempotent
    if profile.raffle_page_completed:
        return redirect(f"{reverse('thank-you')}?entered_raffle=1")

    state = request.GET.get("state")
    response_id = request.GET.get("responseId") or request.GET.get("Q_R")  # Qualtrics sometimes uses Q_R
    q_uid = request.GET.get("uid")
    entered_raffle = (request.GET.get("entered_raffle") or "").strip().lower()

    if not state:
        return HttpResponseBadRequest("Missing state")

    try:
        token = signer.unsign(state, max_age=7200)  # 2 hours
    except SignatureExpired:
        return HttpResponseForbidden("State expired")
    except BadSignature:
        return HttpResponseForbidden("Invalid state")

    if token != (profile.raffle_token or ""):
        return HttpResponseForbidden("Token mismatch")

    # (Optional) sanity check – never use q_uid to choose the account
    if q_uid and str(q_uid) != str(request.user.pk):
        return HttpResponseForbidden("UID mismatch")

    # Mark complete and clear token
    profile.raffle_page_completed = True
    profile.raffle_response_id = response_id or ""
    profile.raffle_token = ""
    profile.raffle_completed_at = timezone.now()
    profile.save(update_fields=[
        "raffle_page_completed",
        "raffle_response_id",
        "raffle_token",
        "raffle_completed_at",
    ])

    # End session + prevent re-entry
    request.user.is_active = False
    request.user.save(update_fields=["is_active"])
    logout(request)

    return redirect(f"{reverse('thank-you')}?entered_raffle={entered_raffle}")


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
            ct = make_aware(datetime.fromisoformat(client_ts))
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
