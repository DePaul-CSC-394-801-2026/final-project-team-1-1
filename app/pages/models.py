import uuid

from django.core.validators import MinLengthValidator
from django.db import models
from datetime import date

#Left, is what is stored, I capitalized the right to be pretty
INTERVAL_CHOICES = [
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("quarterly", "Quarterly"),
    ("yearly", "Yearly"),
]
# use this in build upcoming occurrences
INTERVAL_DAY_MAP = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "quarterly": 91,
    "yearly": 365,
}

#choices for asset category
CATEGORY_CHOICES = [
    ("general", "General"),
    ("appliance", "Appliance"),
    ("furniture", "Furniture")
]
# The user will be what ultimately determines what assets are on their dashboard and what tasks they need to do, etc.
class AppUser(models.Model):
    username = models.CharField(
        primary_key=True,
        max_length=20,
        validators=[MinLengthValidator(5)],
    )
    email = models.EmailField(max_length=254)
    password = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.username} ({self.email})"


# The rooms primary id is a uuid that is automatically generated on creation
# The room is matched to the particular user, when the user is deleted, the room is deleted
# I just set the max length to an arbitrary number, but it should be fine for most instances
class Room(models.Model):
    room_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="rooms")
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

# This splits the data of an asset into a new model
# This allows the original Asset to refer to 
class AssetDetails(models.Model):
    name = models.CharField(max_length=64)
    brand = models.CharField(max_length=64, blank=True)
    model_number = models.CharField(max_length=64, blank=True)

    # This will be null for Assets not created by a user
    owner = models.ForeignKey(AppUser, null=True, blank=True, on_delete=models.CASCADE, related_name="custom_asset_details")

# I did the same uuid pk as the room
# There is also a foreign key to the room, so that we can track which room the asset is in to make sure it appears correctly
# I set arbitrary max length for name and brand fields
# When room is deleted, assets in that room are deleted
class Asset(models.Model):
    asset_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    details = models.ForeignKey(AssetDetails,on_delete=models.CASCADE, related_name="assets", null=True)
    #name = models.CharField(max_length=64)
    #brand = models.CharField(max_length=64, blank=True) # THIS USED AS MANUFACTURER. Could eventually be a constanstant as the other choices above are or something.
    #model_number = models.CharField(max_length=64, blank=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="general")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="assets")

    def __str__(self):
        return f"{self.details.name} ({self.room.name})"

# The task id is a uuid that is automatically generated on creation
# The task is matched to the particular asset, when the asset is deleted, the task is deleted
# The task can also be tied to a room, when the room is deleted, the task is deleted
# Might need to remove the completed
class Task(models.Model):
    INTERVAL_CHOICES = INTERVAL_CHOICES
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64)
    interval = models.CharField(max_length=16, choices=INTERVAL_CHOICES, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    last_completed_date = models.DateField(null=True, blank=True)
    #completed = models.BooleanField(default=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True)

    
#Calculating the number of days between today and next due date
    @property
    def days_until_due(self):
        if not self.next_due_date:
            return None
        delta = self.next_due_date - date.today()
        return delta.days

    def __str__(self):
        location = self.asset.name if self.asset else self.room.name if self.room else "general"
        return f"{self.name} ({location})"

# The consumable id is a uuid that is automatically generated on creation
# The consumable is matched to the particular task, when the task is deleted, the consumable is deleted
# The part number is optional, but if it is present, it will be displayed in the admin page. I think this is what we can use API to get the price of the consumable
# The estimated cost is optional, but if it is present, it will be displayed in the admin page
class Consumable(models.Model):
    consumable_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    details = models.ForeignKey(AssetDetails,on_delete=models.CASCADE, related_name="consumables", null=True)
    #part_number = models.CharField(max_length=64, blank=True)
    #estimated_cost = models.DecimalField(max_digits=9, decimal_places=2, default=0, blank=True)
    #retail_url = models.URLField(blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="consumables")

    def __str__(self):
        return self.details.part_number or self.task.name

# Details for a consumable. Allows for  
class ConsumableDetails(models.Model):
    part_number = models.CharField(max_length=64, blank=True)
    estimated_cost = models.DecimalField(max_digits=9, decimal_places=2, default=0, blank=True)
    retail_url = models.URLField(blank=True)

    # Null for consumable details not made by a user
    owner = models.ForeignKey(AppUser, null=True, blank=True, on_delete=models.CASCADE, related_name="custom_consumable_details")

# The log id is a uuid that is automatically generated on creation
# The log is matched to the particular task, when the task is deleted, the log is deleted
# The completion date is optional, but if it is present, it will be displayed in the admin page
# The cost is optional, but if it is present, it will be displayed in the admin page
# The notes are optional, but if they are present, they will be displayed in the admin page
# The completion date of this could be what resets the duration of the task
class Log(models.Model):
    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    completion_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="logs")

    def __str__(self):
        date = self.completion_date or "pending"
        return f"{self.task.name} on {date}"
