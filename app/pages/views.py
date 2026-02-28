from datetime import datetime, timedelta, date
import re
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from .models import (
    AppUser,
    Asset,
    Home,
    HomeUserConnection,
    Log,
    Room,
    Consumable,
    ConsumableDetails,
    Task,
    INTERVAL_DAY_MAP,
    CATEGORY_CHOICES,
    BRAND_CHOICES,
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

#Use regular expressions for validation
def validate_home_fields(state, zip_code):
    errors = []
    if state:
        if not re.fullmatch(r"[A-Za-z]{2}", state):
            errors.append("State must be a 2-letter code.")
    if zip_code:
        if not re.fullmatch(r"\d{5}(-\d{4})?", zip_code):
            errors.append("Zip Code must be 5 digits or 5+4 digits (12345 or 12345-6789).")
    return errors

# Fetch the current home for the user
def get_current_home(request, user):
    home = None
    #Determine the home for this user
    home_id = request.session.get("home_id")
    #Find that home in the DB if it belongs to the user
    if home_id:
        home = user.homes.filter(home_id=home_id).first()
    if home:
        request.session["home_id"] = str(home.home_id)
        return home
    #If the user doesn't have a home, create one for them
    home = Home.objects.create(name="My Home")
    HomeUserConnection.objects.create(user=user, home=home)
    request.session["home_id"] = str(home.home_id)
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
        home = Home.objects.create(name="My Home")
        HomeUserConnection.objects.create(user=user, home=home)
        messages.success(request, "Account created.")
        return redirect("login")

    return render(request, "register.html")

# This is turning into a disaster and will need to be refactored into the different views per page lol.
def dashboard_view(request):
    if not request.session.get("username"):
        messages.error(request, "Please log in to continue.")
        return redirect("login")

    # Fetch the current users username
    username = request.session["username"]
    user = AppUser.objects.filter(username=username).first()

    home = get_current_home(request, user)

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

        # Switching to a different home
        elif action == "switch-home":
            home_id = request.POST.get("home_id")
            #This could probably be removed. Was used for debugging. Guess its defensive. lol
            new_home = user.homes.filter(home_id=home_id).first() if home_id else None
            if not new_home:
                messages.error(request, "Home not found.")
            else:
                request.session["home_id"] = str(new_home.home_id)
                messages.success(request, "Switched home.")
        
        # Adding an asset
        elif action == "add-asset":
            name = request.POST.get("asset_name", "").strip()
            category = request.POST.get("asset_category", "general").strip().lower() # I fucked up the casing for this flow. Just lowercase everything
            brand = request.POST.get("asset_brand", "").strip()
            model_number = request.POST.get("asset_model_number", "").strip()
            room_id = request.POST.get("asset_room")
            consumable_name = request.POST.get("consumable_name", "").strip()
            consumable_part_number = request.POST.get("consumable_part_number", "").strip()
            consumable_cost = request.POST.get("consumable_cost", "").strip()
            consumable_interval = request.POST.get("consumable_interval", "").strip()
            has_consumable = request.POST.get("asset_has_consumable") == "yes"
            if not has_consumable and any(
                [
                    consumable_name,
                    consumable_part_number,
                    consumable_cost,
                    consumable_interval,
                ]
            ):
                has_consumable = True
            room = None
            if room_id:
                room = rooms_qs.filter(room_id=room_id).first()
            if not room:
                room = selected_room or rooms_qs.first()
            if not room:
                messages.error(request, "Room is required to place assets.")
            elif not name:
                messages.error(request, "Asset name is required.")
            elif category == "appliance" and not brand:
                messages.error(request, "Brand is required for appliances.")
            elif category == "appliance" and has_consumable and not consumable_name:
                messages.error(request, "Consumable name is required.")
            elif category == "appliance" and has_consumable and not consumable_part_number:
                messages.error(request, "Consumable part number is required.")
            elif category == "appliance" and has_consumable and not consumable_cost:
                messages.error(request, "Consumable cost is required.")
            elif category == "appliance" and has_consumable and not consumable_interval:
                messages.error(request, "Consumable interval is required.")
            else:
                estimated_cost = None
                if category == "appliance" and has_consumable:
                    try:
                        estimated_cost = Decimal(consumable_cost)
                    except InvalidOperation:
                        messages.error(request, "Consumable cost could not be read.")
                        return redirect("dashboard")

                asset = Asset.objects.create(
                    name=name,
                    brand=brand,
                    model_number=model_number,
                    category=category,
                    room=room,
                )

                if category == "appliance" and has_consumable:
                    task_next_due = compute_next_due_date(consumable_interval, date.today())
                    consumable = Consumable.objects.create(
                        name=consumable_name,
                        asset=asset,
                    )
                    ConsumableDetails.objects.create(
                        consumable=consumable,
                        part_number=consumable_part_number,
                        estimated_cost=estimated_cost,
                        retail_url="",
                        owner=user,
                    )
                    Task.objects.create(
                        name=f"Replace {consumable_name}",
                        interval=consumable_interval,
                        asset=asset,
                        room=asset.room,
                        home=home,
                        consumable=consumable,
                        last_completed_date=date.today(),
                        next_due_date=task_next_due,
                    )
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
    #Will need to order by due date
    logs = Log.objects.filter(task__in=tasks)
    due_soon_tasks = get_due_soon_tasks(tasks)

    #Everything we are passing to the dashboard page is in the context
    context = {
        "home": home,
        "homes": user.homes.all(),
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
        "brand_choices": BRAND_CHOICES,
    }
    return render(request, "dashboard.html", context)


def manage_homes_view(request):
    # Fetch the current session username
    if not request.session.get("username"):
        messages.error(request, "Please log in to continue.")
        return redirect("login")

    username = request.session["username"]
    user = AppUser.objects.filter(username=username).first()
    home = get_current_home(request, user)

    #
    if request.method == "POST":
        action = request.POST.get("action")

        # Update home details
        if action == "update-home":
            home_name = request.POST.get("home_name", "").strip()
            home_address = request.POST.get("home_address", "").strip()
            home_city = request.POST.get("home_city", "").strip()
            home_state = request.POST.get("home_state", "").strip()
            home_zip = request.POST.get("home_zip", "").strip()
            if not home_name:
                messages.error(request, "Home name is required.")
            else:
                errors = validate_home_fields(home_state, home_zip)
                if errors:
                    for message in errors:
                        messages.error(request, message)
                else:
                    home.name = home_name
                    home.address = home_address
                    home.city = home_city
                    home.state = home_state.upper()
                    home.zip_code = home_zip
                    home.save(update_fields=["name", "address", "city", "state", "zip_code"])
                    messages.success(request, "Home updated.")
        # Add new home per user + home
        elif action == "add-home":
            home_name = request.POST.get("home_name", "").strip()
            home_address = request.POST.get("home_address", "").strip()
            home_city = request.POST.get("home_city", "").strip()
            home_state = request.POST.get("home_state", "").strip()
            home_zip = request.POST.get("home_zip", "").strip()
            if not home_name:
                messages.error(request, "Home name is required.")
            else:
                errors = validate_home_fields(home_state, home_zip)
                if errors:
                    for message in errors:
                        messages.error(request, message)
                else:
                    new_home = Home.objects.create(
                        name=home_name,
                        address=home_address,
                        city=home_city,
                        state=home_state.upper(),
                        zip_code=home_zip,
                    )
                    HomeUserConnection.objects.create(user=user, home=new_home)
                    request.session["home_id"] = str(new_home.home_id)
                    messages.success(request, "Home added and set as current.")

        return redirect("manage_homes")

    context = {
        "home": home,
        "homes": user.homes.all(),
    }
    return render(request, "manage_homes.html", context)


def logout_view(request):
    request.session.pop("username", None)
    messages.success(request, "You are now logged out.")
    return redirect("login")
