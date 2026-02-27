from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from .models import (
    AppUser,
    Asset,
    AssetDetails,
    Home,
    HomeUserConnection,
    Log,
    Room,
    Task,
    INTERVAL_DAY_MAP,
    CATEGORY_CHOICES,
)

DUE_SOON_LIMIT = 5

# ONly surface the five closes task and never resue old occurrences
def get_due_soon_tasks(tasks):
    return tasks.exclude(next_due_date__isnull=True).order_by("next_due_date")[:DUE_SOON_LIMIT]

#Calculate next due date from interval and start date. Could probably refactor this out.
def compute_next_due_date(interval, start_date):
    days = INTERVAL_DAY_MAP.get(interval)
    # if interval is one time
    if not days:
        return start_date
    return start_date + timedelta(days=days)


def get_current_home(user):
    home = user.homes.first()
    if home:
        return home
    home = Home.objects.create(name="My Home", address="")
    HomeUserConnection.objects.create(user=user, home=home)
    return home


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

        user = AppUser.objects.create(username=username, password=password, email=email)
        home = Home.objects.create(name="My Home", address="")
        HomeUserConnection.objects.create(user=user, home=home)
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

    home = get_current_home(user)

    # Fetch rooms for the home
    rooms_qs = Room.objects.filter(home=home)

    #Fetch all assets for the user
    assets_qs = Asset.objects.filter(room__home=home)

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
                Room.objects.create(home=home, name=name, description=description)
                messages.success(request, "Room added for you to organize.")
            else:
                messages.error(request, "Room name is required.")
        
        #Adding a stored asset
        elif action == "add-asset":
            name = request.POST.get("asset_name", "").strip()
            brand = request.POST.get("asset_brand", "").strip()
            category = request.POST.get("asset_category", "general").strip()
            model_number = request.POST.get("asset_model_number", "").strip()
            room_id = request.POST.get("asset_room")
            room = None
            if room_id:
                room = rooms_qs.filter(room_id=room_id).first()
            if not room:
                room = selected_room or rooms_qs.first()
            if not room:
                messages.error(request, "Create a room first to place assets.")
            elif not name:
                messages.error(request, "Asset name is required.")
            else:
                details = AssetDetails.objects.get(brand=brand, name=name, model_number=model_number)
                Asset.objects.create(name=name, details=details, category=category, room=room)

        # If the action is to add a custom asset, get the mandatory asset name, optional brand, optional category and room from the form else throw an error
        elif action == "add-custom-asset":
            name = request.POST.get("asset_name", "").strip()
            brand = request.POST.get("asset_brand", "").strip()
            category = request.POST.get("asset_category", "general").strip()
            model_number = request.POST.get("asset_model_number", "").strip()
            room_id = request.POST.get("asset_room")
            room = None
            if room_id:
                room = rooms_qs.filter(room_id=room_id).first()
            if not room:
                room = selected_room or rooms_qs.first()
            if not room:
                messages.error(request, "Create a room first to place assets.")
            elif not name:
                messages.error(request, "Asset name is required.")
            else:
                details = AssetDetails(name=name, brand=brand, model_number=model_number, owner=user)
                details.save()
                Asset.objects.create(name=name, category=category, details=details, room=room)
                messages.success(request, "Asset added to the room.")

        # If the action is to add a task, get the mandatory task name, optional interval and start date, asset and room from the form else throw an error
        elif action == "add-task":
            name = request.POST.get("task_name", "").strip()
            interval = request.POST.get("task_interval", "").strip()
            start_date_value = request.POST.get("task_start_date", "").strip()
            asset_id = request.POST.get("task_asset")
            room_id = request.POST.get("task_room")

            # If somehow the request goes through without required data expose error
            if not name or not start_date_value:
                messages.error(request, "Task name and start date are required.")
            else:
                # converts string into datetime object and extracts just the date, not the time
                start_date = datetime.fromisoformat(start_date_value).date()
                asset = Asset.objects.filter(asset_id=asset_id, room__home=home).first() if asset_id else None
                room = rooms_qs.filter(room_id=room_id).first() if room_id else None
                if not room:
                    room = selected_room or rooms_qs.first()
                if asset and not room:
                    room = asset.room

                #Create task
                next_due = compute_next_due_date(interval, start_date)

                Task.objects.create(
                    name=name,
                    interval=interval,
                    asset=asset,
                    room=room,
                    home=home,
                    last_completed_date=start_date,
                    next_due_date=next_due,
                )
                messages.success(request, "Task created successfully.")

        # extract form data
        elif action == "add-log":
            task_id = request.POST.get("log_task")
            completion_date_value = request.POST.get("log_completion_date") or None
            notes = request.POST.get("log_notes", "").strip()
            cost_value = request.POST.get("log_cost", "").strip()

            task = Task.objects.filter(home=home, task_id=task_id).first()
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

                # Convert the date string to a date object if provided
                completion_date = None
                if completion_date_value:
                    completion_date = datetime.fromisoformat(completion_date_value).date()

                log = Log.objects.create(task=task, completion_date=completion_date, cost=cost, notes=notes)
                if log.completion_date:
                    task.last_completed_date = log.completion_date
                    task.next_due_date = compute_next_due_date(task.interval, log.completion_date)
                    task.save(update_fields=["last_completed_date", "next_due_date"])
                messages.success(request, "Log recorded for task. :)")
        #Delete action        
        elif action == "delete-task":
            task_id = request.POST.get("task_id")
            task = Task.objects.filter(home=home, task_id=task_id).first()
            if not task:
                messages.error(request, "Task was not found")
            else:
                task.delete()
                messages.success(request, "Task deleted.")
        elif action == "delete-room": 
            room_id = request.POST.get('room_id')
            room = rooms_qs.filter(room_id=room_id).first() if room_id else None
            if not room: 
                messages.error(request, "Room was not found")
            else:
                room.delete()
                messages.success(request, "Room was deleted.")
        #Sort by room
        elif action == "sort-room":
            room_id = request.POST.get("room_id")

            #Get all assets/tasks that belong to rooms owned by the user
            assets = Asset.objects.filter(room__home=home).filter(room=room_id)
            tasks = Task.objects.filter(home=home).filter(Q(room=room_id) | Q(asset__room=room_id))

            #Will need to order by due date
            logs = Log.objects.filter(task__in=tasks)
            due_soon_tasks = get_due_soon_tasks(tasks)

            context = {
                "rooms": rooms_qs,
                "selected_room": selected_room,
                "selected_room_id": selected_room_id,
                "assets": assets,
                "tasks": tasks,
                "due_soon_tasks": due_soon_tasks,
                "logs": logs,
                "asset_choices": Asset.objects.filter(room__home=home),
                "task_choices": Task.objects.filter(home=home),
                "interval_choices": Task.INTERVAL_CHOICES,
                "category_choices": CATEGORY_CHOICES,
            }
            return render(request, "dashboard.html", context)

        elif action == "delete-asset":
            asset_id = request.POST.get("asset_id")
            asset = assets_qs.filter(asset_id=asset_id).first() if asset_id else None
            if not asset:
                messages.error(request, "Asset was not found")
            else:
                asset.delete()
                messages.success(request, "Asset was deleted")
        #Sort by asset
        elif action == "sort-asset":
            asset_id = request.POST.get('asset_id')

            #Get all assets/tasks that belong to rooms owned by the user
            assets = Asset.objects.filter(room__home=home)
            tasks = Task.objects.filter(home=home, asset=asset_id)

            #Will need to order by due date
            logs = Log.objects.filter(task__in=tasks)
            due_soon_tasks = get_due_soon_tasks(tasks)

            context = {
                "rooms": rooms_qs,
                "selected_room": selected_room,
                "selected_room_id": selected_room_id,
                "assets": assets,
                "tasks": tasks,
                "due_soon_tasks": due_soon_tasks,
                "logs": logs,
                "asset_choices": Asset.objects.filter(room__home=home),
                "task_choices": Task.objects.filter(home=home),
                "interval_choices": Task.INTERVAL_CHOICES,
                "category_choices": CATEGORY_CHOICES,
            }
            return render(request, "dashboard.html", context)
        
        return redirect("dashboard")

    #Get all assets/tasks that belong to rooms owned by the user
    assets = Asset.objects.filter(room__home=home)
    tasks = Task.objects.filter(home=home)
    stored_brands = AssetDetails.objects.filter(owner__isnull=True).values_list('brand', flat=True).distinct().order_by('brand')
    stored_asset_details = AssetDetails.objects.filter(owner__isnull=True)



    #Will need to order by due date
    logs = Log.objects.filter(task__in=tasks)
    due_soon_tasks = get_due_soon_tasks(tasks)

    #Everything we are passing to the dashboard page is in the context
    context = {
        "rooms": rooms_qs,
        "selected_room": selected_room,
        "selected_room_id": selected_room_id,
        "assets": assets,
        "stored_brands": stored_brands,
        "stored_asset_details": stored_asset_details,
        "tasks": tasks,
        "due_soon_tasks": due_soon_tasks,
        "logs": logs,
        "asset_choices": Asset.objects.filter(room__home=home),
        "task_choices": Task.objects.filter(home=home),
        "interval_choices": Task.INTERVAL_CHOICES,
        "category_choices": CATEGORY_CHOICES,
    }
    return render(request, "dashboard.html", context)


def logout_view(request):
    request.session.pop("username", None)
    messages.success(request, "You are now logged out.")
    return redirect("login")
