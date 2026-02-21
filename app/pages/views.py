from django.contrib import messages
from django.shortcuts import redirect, render

from .models import AppUser


def search_view(request):
    return render(request, "base.html")


# Login view, just like to-do app
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        try:
            user = AppUser.objects.get(username=username)
        except AppUser.DoesNotExist:
            user = None

        if user is None or user.password != password:
            messages.error(request, "Invalid username or password. :(")
            return render(request, "login.html")

        request.session["username"] = user.username
        messages.success(request, "You are now logged in.")
        return redirect("dashboard")

    return render(request, "login.html")


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        email = request.POST.get("email", "").strip()
        if not (5 <= len(username) <= 20):
            messages.error(request, "Username must be 5-20 characters.")
            return render(request, "register.html")

        if not email:
            messages.error(request, "Please provide an email address.")
            return render(request, "register.html")

        if AppUser.objects.filter(username=username).exists():
            messages.error(request, "That username is already taken.")
            return render(request, "register.html")

        AppUser.objects.create(username=username, password=password, email=email)
        messages.success(request, "Account created.")
        return redirect("login")

    return render(request, "register.html")


def dashboard_view(request):
    if not request.session.get("username"):
        messages.error(request, "Please log in to continue.")
        return redirect("login")

    return render(request, "dashboard.html")


def logout_view(request):
    request.session.pop("username", None)
    messages.success(request, "You are now logged out.")
    return redirect("login")
