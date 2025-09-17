from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


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
