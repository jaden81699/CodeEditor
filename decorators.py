from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache


def editor_url_for(user):
    p = user.participantprofile
    return reverse("control_app:editor") if p.group == "C" else reverse("experimental_app:editor")


def done_url():
    return reverse("thank-you")  # final "Thanks" page


def _eligible_for_raffle(p):
    # Control users can enter raffle immediately if they got all 3 correct on attempt 1.
    # Everyone else must complete the post-assessment first.
    return (p.group == "C" and getattr(p, "control_all_correct", False)) or getattr(p, "post_assessment_completed", False)


def guard_pre(view):
    @wraps(view)
    @never_cache
    def w(request, *a, **kw):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        p = request.user.participantprofile

        # If raffle already completed → done
        if getattr(p, "raffle_page_completed", False):
            return redirect(done_url())

        # If user is already eligible for raffle → raffle
        if _eligible_for_raffle(p) and not getattr(p, "raffle_page_completed", False):
            return redirect("raffle-entry")

        # If post flow already started and not finished → force post
        if getattr(p, "post_assessment_started", False) and not getattr(p, "post_assessment_completed", False):
            return redirect("post-assessment")

        # If pre done but coding not → editor
        if getattr(p, "pre_assessment_completed", False) and not getattr(p, "both_ai_and_non_ai_portion_of_code_assessment_completed", False):
            return redirect(editor_url_for(request.user))

        # If coding done but post not → post
        if getattr(p, "both_ai_and_non_ai_portion_of_code_assessment_completed", False) and not getattr(p, "post_assessment_completed", False):
            return redirect("post-assessment")

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
        if not getattr(p, "pre_assessment_completed", False):
            return redirect("pre-assessment")

        # If raffle already completed → thanks
        if getattr(p, "raffle_page_completed", False):
            return redirect(done_url())

        # If control and all-correct on attempt 1 → raffle (skip post)
        if p.group == "C" and getattr(p, "control_all_correct", False):
            return redirect("raffle-entry")

        # If post already completed but raffle not yet → raffle
        if getattr(p, "post_assessment_completed", False) and not getattr(p, "raffle_page_completed", False):
            return redirect("raffle-entry")

        # If post flow in progress (started but not completed) → post
        if getattr(p, "post_assessment_started", False) and not getattr(p, "post_assessment_completed", False):
            return redirect("post-assessment")

        # If coding already done → post
        if getattr(p, "both_ai_and_non_ai_portion_of_code_assessment_completed", False) and not getattr(p, "post_assessment_completed", False):
            return redirect("post-assessment")

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

        # Need pre + coding done (except control-all-correct users who skip post)
        if not getattr(p, "pre_assessment_completed", False):
            return redirect("pre-assessment")

        # If raffle already completed → thanks
        if getattr(p, "raffle_page_completed", False):
            return redirect(done_url())

        # Control-all-correct skip post → raffle
        if p.group == "C" and getattr(p, "control_all_correct", False):
            return redirect("raffle-entry")

        if not getattr(p, "both_ai_and_non_ai_portion_of_code_assessment_completed", False):
            return redirect(editor_url_for(request.user))

        # If already completed post → raffle (or thanks if raffle done)
        if getattr(p, "post_assessment_completed", False):
            return redirect("raffle-entry")

        # Else show post
        return view(request, *a, **kw)

    return w


def guard_raffle(view):
    @wraps(view)
    @never_cache
    def w(request, *a, **kw):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        p = request.user.participantprofile

        # Must have finished pre
        if not getattr(p, "pre_assessment_completed", False):
            return redirect("pre-assessment")

        # If raffle already completed → thanks
        if getattr(p, "raffle_page_completed", False):
            return redirect(done_url())

        # If eligible → allow raffle views to execute
        if _eligible_for_raffle(p):
            return view(request, *a, **kw)

        # Otherwise force them through the right prerequisites
        if getattr(p, "post_assessment_started", False) and not getattr(p, "post_assessment_completed", False):
            return redirect("post-assessment")

        if not getattr(p, "both_ai_and_non_ai_portion_of_code_assessment_completed", False):
            return redirect(editor_url_for(request.user))

        # Coding done but post not done → post
        return redirect("post-assessment")

    return w
