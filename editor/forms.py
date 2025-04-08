from django import forms
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from .models import Questions, TestCase, QUESTION_TYPE_CHOICES


class QuestionsForm(forms.ModelForm):
    question_type = forms.ChoiceField(
        choices=QUESTION_TYPE_CHOICES,
        widget=forms.RadioSelect,
        label="Question Type"
    )

    class Meta:
        model = Questions
        fields = ['question_string', 'question_type', 'user_starter_code', 'instructor_code']
        widgets = {
            'user_starter_code': forms.Textarea(attrs={'class': 'd-none'}),
            'instructor_code': forms.Textarea(attrs={'class': 'd-none'}),
        }


class TestCaseForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ['test_input', 'expected_output']


# Custom inline formset to perform conditional validation.
class BaseTestCaseFormSet(BaseInlineFormSet):
    def clean(self):
        """
        If the question's type is not UNIT, then each non-deleted test case must have a test_input.
        """
        super().clean()
        # Only check if the parent instance exists.
        if self.instance and self.instance.question_type != 'UNIT':
            for form in self.forms:
                # Skip forms marked for deletion
                if self.can_delete and self._should_delete_form(form):
                    continue
                # If the form is not valid, skip validation here.
                if not form.cleaned_data:
                    continue
                test_input = form.cleaned_data.get('test_input')
                if not test_input:
                    raise forms.ValidationError("Test input is required unless the question type is UNIT.")


# Create the inline formset. Allow one extra empty form and deletion.
TestCaseFormSet = inlineformset_factory(
    parent_model=Questions,
    model=TestCase,
    form=TestCaseForm,
    formset=BaseTestCaseFormSet,
    extra=1,
    can_delete=True
)
