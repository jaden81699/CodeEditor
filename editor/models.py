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
