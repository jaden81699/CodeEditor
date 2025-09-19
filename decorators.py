from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache

from utils import redirect_to_editor_for


def editor_url_for(user):
    p = user.participantprofile
    return reverse('control_app:editor') if p.group == 'C' else reverse('experimental_app:editor')


def done_url():
    return reverse('thank-you')  # or your “thanks” page


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


def block_editor_while_post_survey_incomplete(view):
    @wraps(view)
    def _w(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        p = getattr(request.user, "participantprofile", None)
        # If post started but not completed, force them back to the gate
        if p and p.post_assessment_started and not p.post_assessment_completed:
            return redirect("post-assessment")
        return view(request, *args, **kwargs)

    return _w


def guard_pre(view):
    @wraps(view)
    @never_cache
    def w(request, *a, **kw):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        p = request.user.participantprofile
        # If post flow already started and not finished → force post
        if p.post_assessment_started and not p.post_assessment_completed:
            return redirect('post-assessment')
        # If pre done but coding not → editor
        if p.pre_assessment_completed and not p.both_ai_and_non_ai_portion_of_code_assessment_completed:
            return redirect(editor_url_for(request.user))
        # If coding done but post not → post
        if p.both_ai_and_non_ai_portion_of_code_assessment_completed and not p.post_assessment_completed:
            return redirect('post-assessment')
        # Else show pre
        return view(request, *a, **kw)

    return w


def guard_editor(view):
    @wraps(view)
    @never_cache
    def w(request, *a, **kw):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        p = request.user.participantprofile
        # Must have finished pre
        if not p.pre_assessment_completed:
            return redirect('pre-assessment')
        # If post flow in progress (started but not completed) → post
        if p.post_assessment_started and not p.post_assessment_completed:
            return redirect('post-assessment')
        # If coding already done → post
        if p.both_ai_and_non_ai_portion_of_code_assessment_completed and not p.post_assessment_completed:
            return redirect('post-assessment')
        # If everything done → thanks
        if p.post_assessment_completed:
            return redirect(done_url())
        # Else show editor
        return view(request, *a, **kw)

    return w


def guard_post(view):
    @wraps(view)
    @never_cache
    def w(request, *a, **kw):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        p = request.user.participantprofile
        # Need pre + coding done
        if not p.pre_assessment_completed:
            return redirect('pre-assessment')
        if not p.both_ai_and_non_ai_portion_of_code_assessment_completed:
            return redirect(editor_url_for(request.user))
        # If already completed post → thanks
        if p.post_assessment_completed:
            return redirect(done_url())
        # Else show post
        return view(request, *a, **kw)

    return w
