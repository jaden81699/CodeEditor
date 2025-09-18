from django.shortcuts import redirect


def redirect_to_editor_for(user):
    p = getattr(user, "participantprofile", None)
    if not p:
        return redirect("login")  # if no profile, login/register
    mapping = {
        "C": "control_app:editor",
        "E": "experimental_app:editor",
    }
    return redirect(
        mapping.get(p.group, "login"))  # if assigned to a group, go to the coding question, otherwise, login.
