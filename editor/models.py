from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from django.db import migrations

QUESTION_TYPE_CHOICES = [
    ('IO', 'I/O'),
    ('UNIT', 'Unit'),
]


class Questions(models.Model):
    question_string = models.CharField(max_length=2000)
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES)
    user_starter_code = models.CharField(max_length=20000, default="")
    instructor_code = models.CharField(max_length=20000, default="")

    def __str__(self):
        return self.question_string


class TestCase(models.Model):
    question = models.ForeignKey(Questions, related_name='test_cases', on_delete=models.CASCADE)
    test_input = models.CharField(max_length=2000, blank=True)  # allow blank input for UNIT tests
    expected_output = models.CharField(max_length=2000)

    def __str__(self):
        return f"TestCase for {self.question.id}: Input {self.test_input}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} → {self.score}"


class ParticipantProfile(models.Model):
    """Extra info that doesn’t belong on auth.User."""
    CONTROL = "C"
    EXPERIMENTAL = "E"
    GROUP_CHOICES = [(CONTROL, "Control"), (EXPERIMENTAL, "Experimental")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                primary_key=True, on_delete=models.CASCADE, related_name="participantprofile")
    group = models.CharField(max_length=1, choices=GROUP_CHOICES)
    # first‑round counters
    first_attempt_correct = models.PositiveSmallIntegerField(default=0)
    first_attempt_incorrect = models.PositiveSmallIntegerField(default=0)
    # second‑round counters (only meaningful for the experimental group)
    second_attempt_correct = models.PositiveSmallIntegerField(default=0)
    both_ai_and_non_ai_portion_of_code_assessment_completed = models.BooleanField(
        default=False)  # set this when done with coding

    pre_assessment_completed = models.BooleanField(default=False)
    pre_assessment_response_id = models.CharField(max_length=64, blank=True)
    pre_assessment_token = models.CharField(max_length=64, blank=True)
    pre_assessment_completed_at = models.DateTimeField(null=True, blank=True)
    randomized_at = models.DateTimeField(null=True, blank=True)

    post_assessment_started = models.BooleanField(default=False)
    post_assessment_completed = models.BooleanField(default=False)
    post_assessment_token = models.CharField(max_length=64, blank=True)
    post_assessment_response_id = models.CharField(max_length=64, blank=True)
    post_assessment_completed_at = models.DateTimeField(null=True, blank=True)


class Submission(models.Model):
    """
    One code submission for one question.
    attempt_no: 1 = first round, 2 = redo round …
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey("editor.Questions", on_delete=models.CASCADE)
    attempt_no = models.PositiveSmallIntegerField()  # 1 or 2
    used_ai = models.BooleanField()  # True if Gemini pane allowed
    is_correct = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)


class EnrollmentCap(models.Model):
    """Global caps (set once in admin or migration)"""
    target_C = models.PositiveIntegerField(default=130)
    target_E = models.PositiveIntegerField(default=130)


class RandomizationBlock(models.Model):
    """
    Used for the remaining labels for the current permuted block.
    """
    sequence = models.JSONField(default=list)  # remaining labels in current block, e.g. ["C","E","E","C"]
    block_size = models.PositiveIntegerField(default=6)  # even number: 4, 6, 8...
    updated_at = models.DateTimeField(auto_now=True)


class AITelemetry(models.Model):
    EVENT_CHOICES = [
        ("ai_tab_open", "AI tab opened"),
        ("ai_prompt", "AI prompt sent"),
        ("ai_reply", "AI reply shown"),
        ("paste", "Paste into editor"),
        ("vis_hide", "Page hidden"),
        ("vis_show", "Page visible"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    attempt_no = models.IntegerField(null=True, blank=True)
    question_id = models.IntegerField(null=True, blank=True)
    event = models.CharField(max_length=32, choices=EVENT_CHOICES)
    model_id = models.CharField(max_length=64, blank=True)
    prompt_chars = models.IntegerField(null=True, blank=True)
    reply_chars = models.IntegerField(null=True, blank=True)
    paste_chars = models.IntegerField(null=True, blank=True)
    prompt_hash = models.CharField(max_length=64, blank=True)  # SHA-256 hex of prompt (optional)
    reply_hash = models.CharField(max_length=64, blank=True)  # SHA-256 hex of reply (optional)
    ua = models.TextField(blank=True)  # user-agent (optional)
    client_ts = models.DateTimeField(null=True, blank=True)  # client timestamp (optional)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "attempt_no", "event"]),
            models.Index(fields=["created_at"]),
        ]
