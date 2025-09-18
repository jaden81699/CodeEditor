from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from utils import redirect_to_editor_for


def require_pre_assessment_completed(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        prof = getattr(request.user, "participantprofile", None)
        done = getattr(prof, "pre_assessment_completed", False)  # <- your flag name
        if not done:
            # Send them to your Qualtrics gate (or landing) to complete it
            return redirect("pre-assessment")

        return view_func(request, *args, **kwargs)

    return _wrapped


def require_ready_for_post_assessment_questionnaire(view_func):
    @wraps(view_func)
    def _w(request, *a, **kw):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        p = getattr(request.user, "participantprofile", None)
        if not p or not p.pre_assessment_completed:
            return redirect("pre-assessment")
        if not p.both_ai_and_non_ai_portion_of_code_assessment_completed:
            # send them back to the coding editor to finish
            return redirect_to_editor_for(request.user)
        return view_func(request, *a, **kw)

    return _w
