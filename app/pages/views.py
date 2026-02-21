from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from .models import AppUser, Asset, Log, Room, Task


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

    # Fetch the current users username
    username = request.session["username"]
    user = AppUser.objects.filter(username=username).first()

    # Fetch rooms for the user
    rooms_qs = user.rooms.all()

    #Initially fetch all rooms. TODO add filtering by room
    selected_room_id = request.GET.get("room", "all")
    selected_room = None
    if selected_room_id and selected_room_id != "all":
        selected_room = rooms_qs.filter(room_id=selected_room_id).first()

    # If submitting any form from the dashboard page that is associated with this view
    if request.method == "POST":
        return_room = request.POST.get("return_room", selected_room_id or "all") or "all"
        action = request.POST.get("action")

        # If the action is to add a room, get the mandatory room name and optional description from the form else throw an error
        if action == "add-room":
            name = request.POST.get("room_name", "").strip()
            description = request.POST.get("room_description", "").strip()
            if name:
                Room.objects.create(user=user, name=name, description=description)
                messages.success(request, "Room added for you to organize.")
            else:
                messages.error(request, "Room name is required.")

        # If the action is to add an asset, get the mandatory asset name, optional brand, optional category and room from the form else throw an error
        elif action == "add-asset":
            name = request.POST.get("asset_name", "").strip()
            brand = request.POST.get("asset_brand", "").strip()
            category = request.POST.get("asset_category", "").strip()
            room_id = request.POST.get("asset_room")
            # If room is not specified, default to the first room in the user's rooms. check if asset name is there, else create the opject and add it
            room = rooms_qs.filter(room_id=room_id).first() if room_id else rooms_qs.first()
            if not room:
                messages.error(request, "Create a room first to place assets.")
            elif not name:
                messages.error(request, "Asset name is required.")
            else:
                Asset.objects.create(name=name, brand=brand, category=category, room=room)
                messages.success(request, "Asset added to the room.")

        # If the action is to add a task, get the mandatory task name, optional interval, asset and room from the form else throw an error
        elif action == "add-task":
            name = request.POST.get("task_name", "").strip()
            interval = request.POST.get("task_interval", "").strip()
            asset_id = request.POST.get("task_asset")
            room_id = request.POST.get("task_room")
            # Verify that the asset belongs to the user's rooms else skip query
            asset = Asset.objects.filter(asset_id=asset_id, room__user=user).first() if asset_id else None
            # If room is not specified, default to the first room in the user's rooms.'
            room = rooms_qs.filter(room_id=room_id).first() if room_id else None
            if not name:
                messages.error(request, "Task name is required.")
            else:
                Task.objects.create(name=name, interval=interval, asset=asset, room=room)
                messages.success(request, "Task stub saved.")

        # extract form data
        elif action == "add-log":
            task_id = request.POST.get("log_task")
            completion_date = request.POST.get("log_completion_date") or None
            notes = request.POST.get("log_notes", "").strip()
            cost_value = request.POST.get("log_cost", "").strip()

            # find tasks where either the task is linked to a room owned by the uesr or where it is linked to an asset in a room owned by the user
            # the asset__room__user part is how django can handle foreign keys. Task has an asset, asset has room, room has user. Ya dig? It is like a join statsement where user = user
            task = Task.objects.filter(Q(room__user=user) | Q(asset__room__user=user)).filter(task_id=task_id).first()
            if not task:
                messages.error(request, "Pick a valid task for the log.")
            else:
                cost = None
                if cost_value:
                    try:
                        cost = Decimal(cost_value)
                    except InvalidOperation:
                        cost = None
                        messages.error(request, "Cost could not be read :(")
                Log.objects.create(task=task, completion_date=completion_date, cost=cost, notes=notes)
                messages.success(request, "Log recorded for task. :)")

        #Todo, add filtering implementation. Will need to be handled/returned here. I had the thought above but im tired
        return redirect("dashboard")

    #Get all assets/tasks that belong to rooms owned by the user
    assets = Asset.objects.filter(room__user=user)
    tasks = Task.objects.filter(Q(room__user=user) | Q(asset__room__user=user))

    #Will need to order by due date
    logs = Log.objects.filter(task__in=tasks)
    #Get only five upcoming tasks for now. Needs to be prioritized by due date
    upcoming_tasks = tasks.filter()[:5]

    #Everything we are passing to the dashboard page is in the context
    context = {
        "rooms": rooms_qs,
        "selected_room": selected_room,
        "selected_room_id": selected_room_id,
        "assets": assets,
        "tasks": tasks,
        "upcoming_tasks": upcoming_tasks,
        "logs": logs,
        "asset_choices": Asset.objects.filter(room__user=user),
        "task_choices": Task.objects.filter(Q(room__user=user) | Q(asset__room__user=user))
    }
    return render(request, "dashboard.html", context)


def logout_view(request):
    request.session.pop("username", None)
    messages.success(request, "You are now logged out.")
    return redirect("login")
