import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

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

from CodeEditor import settings
from decorators import *
from editor.forms import QuestionsForm, TestCaseFormSet
from editor.models import Questions, ParticipantProfile, Submission, AICall


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
    })
    resp["Cross-Origin-Opener-Policy"] = "same-origin"
    resp["Cross-Origin-Embedder-Policy"] = "require-corp"
    return resp


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

    # Prevent double-counting if the user submits twice (reload/back/etc.)
    Submission.objects.filter(
        user=request.user,
        attempt_no=exp_pass,
        question_id__in=qids_int,
    ).delete()

    keep_ids = []

    for qid, code, spent_ms in zip(qids_int, codes, time_ms):
        question = get_object_or_404(Questions, pk=qid)

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
                else:
                    is_correct = False
        except Exception as e:
            print("experimental submit_all grading error:", repr(e))
            is_correct = False

        Submission.objects.create(
            user=request.user,
            question=question,
            attempt_no=exp_pass,
            used_ai=(is_exp and exp_pass == 1),
            is_correct=is_correct,
            time_spent_ms=spent_ms,
        )

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
            # For the experimental flow, pass 2 should replay the questions they got CORRECT on pass 1
            request.session["experimental_keep_ids"] = keep_ids
            request.session["experimental_pass"] = 2
            request.session.modified = True

            # If they didn't get any correct on pass 1, there is nothing to replay; skip forward
            if not keep_ids:
                request.user.is_active = False
                request.user.save(update_fields=["is_active"])
                logout(request)  # end the current session
                return JsonResponse({
                    "next": "thank-you",
                    "redirect_url": reverse("thank-you")
                })

            return JsonResponse({
                "next": "second-pass",
                "redirect_url": reverse("experimental_app:editor")
            })

        profile.both_ai_and_non_ai_portion_of_code_assessment_completed = True
        profile.save()
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
                mode=mode,
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
                prompt_tokens=usage.get("input_tokens"),
                completion_tokens=usage.get("output_tokens"),
                total_tokens=usage.get("total_tokens"),
                latency_ms=latency_ms,
            )

        return JsonResponse({"text": out_text})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


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
