import csv
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Max, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST
from openai import OpenAI
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse

from CodeEditor import settings
from decorators import *
from editor.forms import QuestionsForm, TestCaseFormSet
from editor.models import Questions, ParticipantProfile, Submission, AICall
from method_and_class_validator import _validate_submission_contract

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
    Returns (started_at, deadline_at) for the requested coding pass.
    If pass_no is omitted, default to the current experimental_pass in session.
    """
    if pass_no is None:
        pass_no = request.session.get("experimental_pass", 1)
    return _ensure_coding_window(request, pass_no)


def _clear_coding_window(request):
    request.session.pop(CODING_WINDOW_START_KEY, None)
    request.session.pop(CODING_WINDOW_DEADLINE_KEY, None)
    request.session.pop(CODING_WINDOW_PASS_KEY, None)
    request.session.modified = True


def _difficulty_label(question) -> str:
    """Return a human-friendly difficulty label if the field exists."""
    getter = getattr(question, "get_difficulty_display", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            pass
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


@login_required(login_url='login')
@guard_editor
@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True, max_age=0, private=True)
def editor(request):
    profile = request.user.participantprofile
    is_experimental = (profile.group == ParticipantProfile.EXPERIMENTAL)

    # which pass are they on? 1 = AI-enabled pass, 2 = no-AI redo on missed questions
    exp_pass = request.session.get("experimental_pass", 1)
    redo_mode = (exp_pass == 2)

    # pick questions + AI visibility
    # Pass 1: AI-enabled, show the full set
    # Pass 2: NO-AI, replay ONLY the questions they got correct on pass 1
    if exp_pass == 1:
        questions = Questions.objects.order_by("id")[:3]
        show_ai = True
    else:
        keep_ids = request.session.get("experimental_keep_ids", [])
        if not keep_ids:
            # Fallback (e.g., older sessions): derive from attempt 1 correct submissions
            keep_ids = list(Submission.objects.filter(
                user=request.user, attempt_no=1, is_correct=True
            ).values_list("question_id", flat=True))
            request.session["experimental_keep_ids"] = keep_ids
            request.session.modified = True

        if not keep_ids:
            # Still nothing to replay (they passed none on pass 1); push them forward.
            return redirect("thank-you")

        questions = Questions.objects.filter(id__in=keep_ids).order_by("id")
        show_ai = False

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

    coding_started_at, coding_deadline_at = _ensure_coding_window(request, exp_pass)
    now = timezone.now()
    remaining_seconds = max(0, int((coding_deadline_at - now).total_seconds()))

    resp = render(request, "experimental_app/editor.html", {
        "questions": questions,
        "is_experimental": is_experimental,
        "redo_mode": redo_mode,
        "show_ai": show_ai,
        "exp_pass": exp_pass,
        "attempt_no": exp_pass,

        "first_correct": first_correct,
        "second_correct": second_correct,

        "attempt_lists": attempt_lists,
        "improved_qids": improved_qids,
        "attempt1_difficulty_summary": attempt1_difficulty_summary,
        "attempt2_difficulty_summary": attempt2_difficulty_summary,

        # optional profile counters (if your template uses them)
        "first_score": profile.first_attempt_correct,
        "exp_failed": profile.first_attempt_incorrect,

        "coding_deadline_epoch_ms": int(coding_deadline_at.timestamp() * 1000),
        "coding_remaining_seconds": remaining_seconds,
        "coding_limit_seconds": _coding_limit_for_pass(exp_pass),
    })
    resp["Cross-Origin-Opener-Policy"] = "same-origin"
    resp["Cross-Origin-Embedder-Policy"] = "require-corp"
    return resp


@login_required(login_url='login')
@require_POST
def run_code(request):
    code = (request.POST.get("code") or "").strip()
    qid = request.POST.get("question_id")

    exp_pass = request.session.get("experimental_pass", 1)
    _, coding_deadline_at = _get_coding_window(request, exp_pass)
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

    # Validate class name / method contract before running the harness
    contract_error = _validate_submission_contract(question, code)
    if contract_error:
        return JsonResponse({"error": contract_error}, status=200)

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


@login_required(login_url='login')
@require_POST
def submit_all(request):
    """
    Handles *all* question submissions in one POST (experimental group).

    Accepts either:
      1) form-encoded payload:
            question_id=<id>&code=<code>&time_spent_ms=<ms>  (repeated for each question)
      2) JSON payload:
            {"submissions":[{"question_id":1,"code":"...","time_spent_ms":1234}, ...]}

    Notes:
    - attempt_no is derived from the server-side session (experimental_pass) to prevent tampering.
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
        cap = 24 * 60 * 60 * 1000  # 24 hours
        if ms > cap:
            ms = cap
        return ms

    time_ms = [_parse_ms(v) for v in time_spent_raw]
    if len(time_ms) < len(qids_int):
        time_ms.extend([0] * (len(qids_int) - len(time_ms)))
    elif len(time_ms) > len(qids_int):
        time_ms = time_ms[:len(qids_int)]

    profile = request.user.participantprofile
    is_exp = (profile.group == ParticipantProfile.EXPERIMENTAL)

    # First-pass (AI) or second-pass (no AI)?
    exp_pass = request.session.get("experimental_pass", 1)

    keep_ids = []

    for qid, code, spent_ms in zip(qids_int, codes, time_ms):
        question = get_object_or_404(Questions, pk=qid)

        compile_err = ""
        runtime_err = ""
        results = []

        try:
            if question.question_type == "IO":
                results, compile_err, runtime_err = grade_io_question(question, code)
            else:
                # placeholder for UNIT
                results = []
        except Exception as e:
            compile_err = (compile_err + "\n" + repr(e)).strip()
            results = []

        total = len(results)
        passed_count = sum(1 for r in results if r["passed"])
        failed_ids = [r["test_case_id"] for r in results if not r["passed"]]

        is_correct = (total > 0 and passed_count == total and not compile_err)

        # Instead of delete+create, update or create the single row for this attempt
        Submission.objects.update_or_create(
            user=request.user,
            question=question,
            attempt_no=exp_pass,
            defaults={
                "used_ai": (is_exp and exp_pass == 1),
                "is_correct": is_correct,
                "time_spent_ms": spent_ms,
                "code": code,
                "total_test_cases": total,
                "passed_test_cases": passed_count,
                "failed_testcase_ids": failed_ids,
                "compile_error": compile_err,
                "runtime_error": runtime_err,
            }
        )
        print("PASS", exp_pass, "Q", qid, "total", total, "passed", passed_count, "compile?", bool(compile_err),
              "is_correct", is_correct)

        if exp_pass == 1 and is_correct:
            keep_ids.append(question.id)

    # Recompute counters from DB (idempotent + also works for pass 2)
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

    if is_exp:
        if exp_pass == 1:
            # If they didn't get any correct on pass 1, there is nothing to replay; skip forward
            if not keep_ids:
                profile.exp_all_wrong = True
                profile.save(update_fields=["exp_all_wrong"])

                request.session.pop("experimental_keep_ids", None)
                request.session.pop("experimental_pass", None)
                request.session.modified = True
                _clear_coding_window(request)
                return JsonResponse({
                    "next": "raffle-entry",
                    "redirect_url": reverse("raffle-entry")
                })

            # For the experimental flow, pass 2 should replay the questions they got CORRECT on pass 1
            request.session["experimental_keep_ids"] = keep_ids
            request.session["experimental_pass"] = 2
            request.session.modified = True
            _clear_coding_window(request)
            return JsonResponse({
                "next": "second-pass",
                "redirect_url": reverse("experimental_app:editor")
            })

        profile.both_ai_and_non_ai_portion_of_code_assessment_completed = True
        profile.save()
        _clear_coding_window(request)
        return JsonResponse({
            "status": "redirect",
            "redirect_url": reverse("post-assessment")
        })

    return HttpResponse("An unexpected error has occurred")


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.1-codex-mini")
DEFAULT_MAX_OUT = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "800"))

HINTS_SYSTEM_PROMPT = """You are an expert programming assistant. When given a coding problem, produce a correct 
solution and be explicit about assumptions. The target language produced will always be Java (remember to include 
correct imports). Output code for a single public class Solution and include only the methods needed. Do not invent 
constraints; rely only on what the user provided. If something is ambiguous, ask a short clarifying question first. 
After the solution, include reasoning.
Java requirement: Use proper generics (no raw types). Any collections must be parameterized (e.g., Deque<Integer>), and code must compile in Java and formatted in java.
"""


@require_POST
@login_required(login_url="login")
@guard_editor
def ai_respond(request):
    try:
        client = get_openai_client()
        payload = json.loads(request.body.decode("utf-8"))
        user_text = (payload.get("text") or "").strip()
        if not user_text:
            return JsonResponse({"error": "Empty prompt."}, status=400)

        # 🔒 Lock system prompt server-side (ignore any client override)
        instructions = HINTS_SYSTEM_PROMPT

        # Light metadata (IDs only)
        attempt_no = payload.get("attempt_no")
        try:
            attempt_no = int(attempt_no) if attempt_no is not None else None
        except Exception:
            attempt_no = None

        question_id = payload.get("question_id")
        try:
            question_id = int(question_id) if question_id is not None else None
        except Exception:
            question_id = None

        mode = (payload.get("mode") or "").strip().lower()[:16]  # optional label

        # Conversation grouping (per user + attempt + question)
        conv = f"u{request.user.id}:a{attempt_no or 0}:q{question_id or 0}"

        # Server-controlled history window
        history_window = 4

        start = time.time()
        with transaction.atomic():
            last = (AICall.objects
            .select_for_update()
            .filter(conversation_id=conv)
            .aggregate(mx=Max("turn_index"))["mx"])
            turn_index = int(last + 1) if last is not None else 0

            history_qs = (AICall.objects
                          .filter(conversation_id=conv)
                          .order_by("-turn_index")
                          .only("id", "user_text", "assistant_text")[:history_window])
            history_turns = list(reversed(list(history_qs)))
            history_ids = [str(t.id) for t in history_turns]

            row = AICall.objects.create(
                user=request.user,
                question_id=question_id,
                attempt_no=attempt_no,
                conversation_id=conv,
                turn_index=turn_index,
                user_text=user_text,
                history_turn_ids_sent=history_ids,
                history_window_size=len(history_ids),
            )

        # Build prompt string from DB history + current user message
        parts = []
        if history_turns:
            parts.append("Conversation so far:")
            for t in history_turns:
                parts.append(f"USER: {t.user_text}")
                if (t.assistant_text or "").strip():
                    parts.append(f"ASSISTANT: {t.assistant_text}")
            parts.append("")
        parts.append(f"USER: {user_text}")
        prompt = "\n".join(parts)

        resp = client.responses.create(
            model=DEFAULT_MODEL,
            input=prompt,
            instructions=instructions,
            max_output_tokens=DEFAULT_MAX_OUT,
            service_tier="default",
            store=False,
            truncation="auto",
            metadata={
                "conversation_id": conv,
                "turn_index": str(turn_index),
                "question_id": str(question_id or ""),
                "attempt_no": str(attempt_no or ""),
                "mode": mode,
            },
        )

        latency_ms = int((time.time() - start) * 1000)
        out_text = resp.output_text or ""

        usage = getattr(resp, "usage", None) or {}
        if not isinstance(usage, dict):
            usage = {}

        with transaction.atomic():
            AICall.objects.filter(id=row.id).update(
                assistant_text=out_text,
                openai_response_id=str(getattr(resp, "id", "") or ""),
                model=str(DEFAULT_MODEL),
            )

        return JsonResponse({"text": out_text})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def grade_io_question(question: Questions, user_code: str):
    """
    Returns:
      results: list of dicts with {test_case_id, passed, input, expected_output, actual_output}
      compile_err: str
      runtime_err: str
    """
    harness = (question.harness_code or "").strip()
    if not harness:
        raise RuntimeError("Missing harness_code")

    # Stable order so "index" is consistent
    test_cases = list(question.test_cases.all().order_by("id"))

    results = []
    compile_err = ""
    runtime_err = ""

    with tempfile.TemporaryDirectory() as tmp:
        cp = compile_java_sources(tmp, {
            "Solution.java": user_code,
            "Main.java": harness,
        })

        if cp.returncode != 0:
            compile_err = (cp.stderr or "").strip()
            # If compile fails, we can treat all test cases as failed (or return empty results).
            # Returning all failed IDs is usually better for analytics.
            for tc in test_cases:
                results.append({
                    "test_case_id": tc.id,
                    "passed": False,
                    "input": tc.test_input,
                    "expected_output": tc.expected_output.strip(),
                    "actual_output": "",
                })
            return results, compile_err, runtime_err

        for tc in test_cases:
            try:
                out = execute_java_file("Main", tmp, input_data=tc.test_input)
                expected = tc.expected_output.strip()
                actual = (out or "").strip()
                passed = (actual == expected)
            except Exception as e:
                runtime_err = (runtime_err + "\n" + repr(e)).strip()
                expected = tc.expected_output.strip()
                actual = ""
                passed = False

            results.append({
                "test_case_id": tc.id,
                "passed": passed,
                "input": tc.test_input,
                "expected_output": expected,
                "actual_output": actual,
            })

    return results, compile_err, runtime_err


def compile_java_sources(temp_dir: str, sources: dict[str, str]) -> subprocess.CompletedProcess:
    """
    sources example:
      {
        "Solution.java": "<user code>",
        "Main.java": "<harness code>"
      }
    Writes files into temp_dir and compiles them together.
    """
    for filename, src in sources.items():
        Path(temp_dir, filename).write_text(src, encoding="utf-8")

    # compile in the temp dir so the class outputs land there
    return subprocess.run(
        ["javac", *sources.keys()],
        cwd=temp_dir,
        capture_output=True,
        text=True
    )


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


def get_openai_client():
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        # fall back to environment variable if you prefer:
        # api_key = os.environ.get("OPENAI_API_KEY")
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


# ============================================================
# Study Data Export Views
# ============================================================

MANUAL_RECOVERY_ROWS = {
    # Participant 20 manually recovered second-attempt submissions
    # Format: (user_id, question_id, attempt_no)
    (20, 2, 2),
    (20, 3, 2),
}


def _clean_csv_value(value):
    """Keep CSV cells safe and readable."""
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _normalize_code_for_export(code):
    """
    Normalizes code for conservative same-code checks.
    Removes comments and whitespace, but keeps the actual code tokens.
    """
    if not code:
        return ""

    code = str(code)

    # Remove block comments
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)

    # Remove line comments
    code = re.sub(r"//.*", "", code)

    # Remove all whitespace
    code = re.sub(r"\s+", "", code)

    return code.strip()


def _question_difficulty_label(question):
    if not question:
        return ""

    getter = getattr(question, "get_difficulty_display", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            pass

    raw = getattr(question, "difficulty", "") or ""
    mapping = {
        "EASY": "Easy",
        "MED": "Medium",
        "HARD": "Hard",
    }
    return mapping.get(raw, raw)


def _question_difficulty_code(question):
    label = _question_difficulty_label(question)
    mapping = {
        "Easy": 1,
        "Medium": 2,
        "Hard": 3,
    }
    return mapping.get(label, "")


def _group_code(group):
    if group == ParticipantProfile.CONTROL:
        return 0
    if group == ParticipantProfile.EXPERIMENTAL:
        return 1
    return ""


def _question_context(group, attempt_no):
    """
    Helps distinguish unfair comparison contexts.

    C attempt 1 = first exposure without AI
    C attempt 2 = retry after wrong attempt 1, with AI
    E attempt 1 = first exposure with AI
    E attempt 2 = retest after correct attempt 1, without AI
    """
    if group == ParticipantProfile.CONTROL and attempt_no == 1:
        return "first_exposure_no_ai"

    if group == ParticipantProfile.CONTROL and attempt_no == 2:
        return "control_retry_after_wrong_with_ai"

    if group == ParticipantProfile.EXPERIMENTAL and attempt_no == 1:
        return "first_exposure_ai"

    if group == ParticipantProfile.EXPERIMENTAL and attempt_no == 2:
        return "experimental_retest_after_ai_correct_no_ai"

    return "unknown"


def _error_category(submission):
    """
    Conservative analysis category for SPSS/R/Excel.
    This does not change the raw grading; it just classifies the result.
    """
    if submission.is_correct:
        return "correct"

    compile_error = (submission.compile_error or "").strip()
    runtime_error = (submission.runtime_error or "").strip()

    if compile_error:
        return "compile_error"

    if runtime_error:
        return "runtime_error_or_timeout"

    submitted_norm = _normalize_code_for_export(submission.code)
    starter_norm = _normalize_code_for_export(getattr(submission.question, "user_starter_code", ""))

    if not submitted_norm:
        return "starter_or_blank"

    if starter_norm and submitted_norm == starter_norm:
        return "starter_or_blank"

    # Common incomplete patterns: method body present but no return for a return-based task.
    if "return" not in (submission.code or ""):
        return "starter_or_incomplete"

    return "wrong_logic_or_output"


def _safe_pass_rate(passed, total):
    try:
        if total:
            return round(float(passed) / float(total), 4)
    except Exception:
        pass
    return ""


def _actual_ai_call_count_map():
    """
    Returns counts keyed by (user_id, question_id, attempt_no).
    This lets us distinguish:
    - AI available from Submission.used_ai
    - actual AI use from AICall records
    """
    counts = {}

    calls = AICall.objects.exclude(question_id__isnull=True)

    for call in calls:
        key = (call.user_id, call.question_id, call.attempt_no)
        counts[key] = counts.get(key, 0) + 1

    return counts


def _submission_lookup():
    """
    Lookup submissions by (user_id, question_id, attempt_no)
    so we can compute same-code and retention variables.
    """
    lookup = {}

    submissions = Submission.objects.select_related("question").all()

    for sub in submissions:
        key = (sub.user_id, sub.question_id, sub.attempt_no)
        lookup[key] = sub

    return lookup


@staff_member_required
def export_dashboard(request):
    """
    Admin-only export dashboard.

    URL: /admin-export/
    """
    return render(request, "admin_export.html")


@staff_member_required
def export_submission_level_csv(request):
    """
    One row per participant/question/attempt.

    This is the most important CSV for SPSS because it preserves:
    - group
    - attempt
    - question difficulty
    - AI availability
    - actual AI use
    - correctness
    - error category
    - conservative maintenance variables
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="submission_level_export.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "user_id",
        "username",
        "group",
        "group_code",
        "attempt_no",
        "question_id",
        "question_name",
        "difficulty",
        "difficulty_code",
        "question_context",

        "ai_available",
        "actual_ai_used",
        "ai_call_count_for_question",

        "is_correct",
        "passed_test_cases",
        "total_test_cases",
        "testcase_pass_rate",
        "failed_testcase_ids",

        "compile_error_present",
        "runtime_error_present",
        "error_category",

        "starter_or_blank_code",
        "same_code_as_prior_attempt",
        "same_code_as_prior_ai_attempt",

        "experimental_retention_eligible",
        "raw_no_ai_retained",
        "conservative_no_ai_maintained",

        "time_spent_ms",
        "time_spent_seconds",
        "zero_time_flag",
        "manual_recovery",

        "timestamp",
    ])

    ai_counts = _actual_ai_call_count_map()
    sub_lookup = _submission_lookup()

    submissions = (
        Submission.objects
        .select_related("user", "question", "user__participantprofile")
        .order_by("user_id", "attempt_no", "question_id")
    )

    for sub in submissions:
        user = sub.user

        try:
            profile = user.participantprofile
            group = profile.group
        except ParticipantProfile.DoesNotExist:
            group = ""

        question = sub.question
        question_name = getattr(question, "question_name", "") or f"Question {question.id}"
        difficulty = _question_difficulty_label(question)
        difficulty_code = _question_difficulty_code(question)

        ai_key = (sub.user_id, sub.question_id, sub.attempt_no)
        ai_call_count = ai_counts.get(ai_key, 0)

        ai_available = 1 if sub.used_ai else 0
        actual_ai_used = 1 if ai_call_count > 0 else 0

        compile_error_present = 1 if (sub.compile_error or "").strip() else 0
        runtime_error_present = 1 if (sub.runtime_error or "").strip() else 0

        error_category = _error_category(sub)
        starter_or_blank_code = 1 if error_category in {
            "starter_or_blank",
            "starter_or_incomplete",
        } else 0

        current_code_norm = _normalize_code_for_export(sub.code)

        prior_sub = sub_lookup.get((sub.user_id, sub.question_id, sub.attempt_no - 1))
        prior_code_norm = _normalize_code_for_export(prior_sub.code) if prior_sub else ""

        same_code_as_prior_attempt = 1 if prior_code_norm and current_code_norm == prior_code_norm else 0

        same_code_as_prior_ai_attempt = 0
        experimental_retention_eligible = 0
        raw_no_ai_retained = ""
        conservative_no_ai_maintained = ""

        # Experimental group attempt 2 = no-AI retest after AI-supported success.
        if group == ParticipantProfile.EXPERIMENTAL and sub.attempt_no == 2:
            ai_attempt_sub = sub_lookup.get((sub.user_id, sub.question_id, 1))

            if ai_attempt_sub and ai_attempt_sub.is_correct:
                experimental_retention_eligible = 1
                raw_no_ai_retained = 1 if sub.is_correct else 0

                ai_attempt_code_norm = _normalize_code_for_export(ai_attempt_sub.code)
                same_code_as_prior_ai_attempt = (
                    1 if ai_attempt_code_norm and current_code_norm == ai_attempt_code_norm else 0
                )

                conservative_no_ai_maintained = (
                    1 if sub.is_correct and not same_code_as_prior_ai_attempt else 0
                )

        time_seconds = ""
        try:
            time_seconds = round(float(sub.time_spent_ms) / 1000.0, 3)
        except Exception:
            pass

        zero_time_flag = 1 if sub.time_spent_ms == 0 else 0
        manual_recovery = 1 if (sub.user_id, sub.question_id, sub.attempt_no) in MANUAL_RECOVERY_ROWS else 0

        writer.writerow([
            sub.user_id,
            _clean_csv_value(user.username),
            group,
            _group_code(group),
            sub.attempt_no,
            sub.question_id,
            _clean_csv_value(question_name),
            difficulty,
            difficulty_code,
            _question_context(group, sub.attempt_no),

            ai_available,
            actual_ai_used,
            ai_call_count,

            1 if sub.is_correct else 0,
            sub.passed_test_cases,
            sub.total_test_cases,
            _safe_pass_rate(sub.passed_test_cases, sub.total_test_cases),
            _clean_csv_value(sub.failed_testcase_ids),

            compile_error_present,
            runtime_error_present,
            error_category,

            starter_or_blank_code,
            same_code_as_prior_attempt,
            same_code_as_prior_ai_attempt,

            experimental_retention_eligible,
            raw_no_ai_retained,
            conservative_no_ai_maintained,

            sub.time_spent_ms,
            time_seconds,
            zero_time_flag,
            manual_recovery,

            _clean_csv_value(sub.timestamp),
        ])

    return response


@staff_member_required
def export_participant_summary_csv(request):
    """
    One row per participant.

    Useful for high-level analyses:
    - completion status
    - total correctness
    - total AI use
    - participant-level flags
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="participant_summary_export.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "user_id",
        "username",
        "group",
        "group_code",

        "pre_assessment_completed",
        "coding_completed",
        "post_assessment_started",
        "post_assessment_completed",
        "raffle_page_completed",

        "first_attempt_correct_profile",
        "first_attempt_incorrect_profile",
        "second_attempt_correct_profile",

        "attempt1_submission_count",
        "attempt1_correct_count",
        "attempt1_incorrect_count",

        "attempt2_submission_count",
        "attempt2_correct_count",
        "attempt2_incorrect_count",

        "total_submission_count",
        "total_correct_count",
        "total_incorrect_count",

        "total_ai_calls",
        "ai_calls_attempt1",
        "ai_calls_attempt2",
        "actual_ai_user_any",

        "zero_time_submission_count",
        "starter_or_blank_submission_count",
        "compile_error_submission_count",
        "runtime_error_submission_count",

        "manual_recovery_flag",
        "exclude_complete_case_flag",
        "notes",
    ])

    profiles = (
        ParticipantProfile.objects
        .select_related("user")
        .filter(group__in=[
            ParticipantProfile.CONTROL,
            ParticipantProfile.EXPERIMENTAL,
        ])
        .order_by("user_id")
    )

    ai_counts_by_user = {}
    ai_counts_by_user_attempt = {}

    for call in AICall.objects.all():
        ai_counts_by_user[call.user_id] = ai_counts_by_user.get(call.user_id, 0) + 1

        key = (call.user_id, call.attempt_no)
        ai_counts_by_user_attempt[key] = ai_counts_by_user_attempt.get(key, 0) + 1

    for profile in profiles:
        user = profile.user
        subs = Submission.objects.filter(user=user).select_related("question")

        attempt1 = subs.filter(attempt_no=1)
        attempt2 = subs.filter(attempt_no=2)

        total_submission_count = subs.count()
        total_correct_count = subs.filter(is_correct=True).count()
        total_incorrect_count = subs.filter(is_correct=False).count()

        zero_time_count = subs.filter(time_spent_ms=0).count()
        compile_error_count = subs.exclude(compile_error="").count()
        runtime_error_count = subs.exclude(runtime_error="").count()

        starter_count = 0
        for sub in subs:
            if _error_category(sub) in {"starter_or_blank", "starter_or_incomplete"}:
                starter_count += 1

        manual_recovery_flag = 1 if user.id == 20 else 0

        exclude_complete_case_flag = 0
        notes = []

        if not profile.post_assessment_completed or not profile.raffle_page_completed:
            exclude_complete_case_flag = 1
            notes.append("Incomplete post/raffle flow")

        if not profile.both_ai_and_non_ai_portion_of_code_assessment_completed:
            exclude_complete_case_flag = 1
            notes.append("Coding flow incomplete")

        if user.id == 20:
            notes.append(
                "Manual second-attempt recovery after platform submission failure; exclude manual rows from timing analysis")

        if zero_time_count:
            notes.append("Contains zero-time submission rows")

        writer.writerow([
            user.id,
            _clean_csv_value(user.username),
            profile.group,
            _group_code(profile.group),

            1 if profile.pre_assessment_completed else 0,
            1 if profile.both_ai_and_non_ai_portion_of_code_assessment_completed else 0,
            1 if profile.post_assessment_started else 0,
            1 if profile.post_assessment_completed else 0,
            1 if profile.raffle_page_completed else 0,

            profile.first_attempt_correct,
            profile.first_attempt_incorrect,
            profile.second_attempt_correct,

            attempt1.count(),
            attempt1.filter(is_correct=True).count(),
            attempt1.filter(is_correct=False).count(),

            attempt2.count(),
            attempt2.filter(is_correct=True).count(),
            attempt2.filter(is_correct=False).count(),

            total_submission_count,
            total_correct_count,
            total_incorrect_count,

            ai_counts_by_user.get(user.id, 0),
            ai_counts_by_user_attempt.get((user.id, 1), 0),
            ai_counts_by_user_attempt.get((user.id, 2), 0),
            1 if ai_counts_by_user.get(user.id, 0) > 0 else 0,

            zero_time_count,
            starter_count,
            compile_error_count,
            runtime_error_count,

            manual_recovery_flag,
            exclude_complete_case_flag,
            "; ".join(notes),
        ])

    return response


@staff_member_required
def export_ai_calls_csv(request):
    """
    One row per AI call.

    Useful for qualitative coding:
    - prompt type
    - debugging vs clarification vs solution request
    - actual AI use by question
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="ai_calls_export.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "ai_call_id",
        "user_id",
        "username",
        "group",
        "group_code",
        "attempt_no",
        "question_id",
        "question_name",
        "difficulty",
        "difficulty_code",
        "conversation_id",
        "turn_index",
        "model",
        "user_text",
        "assistant_text",
        "history_window_size",
        "created_at",
    ])

    calls = (
        AICall.objects
        .select_related("user", "question", "user__participantprofile")
        .order_by("user_id", "attempt_no", "question_id", "created_at")
    )

    for call in calls:
        user = call.user

        try:
            profile = user.participantprofile
            group = profile.group
        except ParticipantProfile.DoesNotExist:
            group = ""

        question = call.question
        question_id = question.id if question else ""
        question_name = getattr(question, "question_name", "") if question else ""
        difficulty = _question_difficulty_label(question) if question else ""
        difficulty_code = _question_difficulty_code(question) if question else ""

        writer.writerow([
            call.id,
            call.user_id,
            _clean_csv_value(user.username),
            group,
            _group_code(group),
            call.attempt_no,
            question_id,
            _clean_csv_value(question_name),
            difficulty,
            difficulty_code,
            _clean_csv_value(call.conversation_id),
            call.turn_index,
            _clean_csv_value(call.model),
            _clean_csv_value(call.user_text),
            _clean_csv_value(call.assistant_text),
            call.history_window_size,
            _clean_csv_value(call.created_at),
        ])

    return response
