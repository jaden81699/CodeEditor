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
