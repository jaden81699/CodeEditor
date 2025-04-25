from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView

from editor.models import ParticipantProfile, Questions
from editor.forms import QuestionsForm, TestCaseFormSet
from editor.views import submit_code as core_submit, editor as core_editor


def register_control(request):
    """
    A single page that offers both Login and Register tabs.
    We auto‐generate the username as the new User.pk.
    """
    # Prepare an empty login form for either GET or POST
    login_form = AuthenticationForm()

    if request.method == "POST":
        # Grab the two password fields directly
        pwd1 = request.POST.get("password1")
        pwd2 = request.POST.get("password2")

        # If passwords are empty or don’t match, redisplay Register tab with error
        if not pwd1 or pwd1 != pwd2:
            return render(request, "control_app/login_register_c.html", {
                "form": login_form,
                "register_error": "Passwords must match and not be empty.",
                # no generated_username → stays on Register tab
            })

        # 1) Create a temporary user, so we get an auto PK
        temp_user = User.objects.create_user(username="temp", password=pwd1)

        # 2) Take its PK, convert to string, overwrite username
        new_username = str(temp_user.id)
        temp_user.username = new_username
        temp_user.save()

        # 3) Assign them to Control group
        profile = temp_user.participantprofile
        profile.group = "C"
        profile.save()

        # 4) Re‐render the SAME page, but now show the success banner + Login tab
        return render(request, "control_app/login_register_c.html", {
            "generated_username": new_username,
            "form": AuthenticationForm(),  # fresh login form
            # we can show a fresh placeholder register form or leave it out
        })

    # GET: just render both blank forms
    return render(request, "control_app/login_register_c.html", {
        "form": login_form,
    })


class ControlLoginView(LoginView):
    template_name = "control_app/login_register_c.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("editor")

    def get_success_url(self):
        return self.success_url


@login_required
def editor(request):
    # delegate to your core editor view, but it will see request.user.participantprofile.group == 'C'
    return core_editor(request)


@login_required
def submit_code(request):
    # delegate to your core submit_code, it will record first/second attempt
    return core_submit(request)


@login_required
def run_code(request):
    # you can either import and call your core run_code or re-alias it
    from editor.views import run_code as core_run
    return core_run(request)


def thank_you(request):
    return render(request, "control_app/thank_you.html")


def logout_view(request):
    """Logout user and redirect to login page."""
    logout(request)
    return redirect('control_app:login')
