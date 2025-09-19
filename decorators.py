from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache


def editor_url_for(user):
    p = user.participantprofile
    return reverse('control_app:editor') if p.group == 'C' else reverse('experimental_app:editor')


def done_url():
    return reverse('thank-you')  # or your “thanks” page


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
