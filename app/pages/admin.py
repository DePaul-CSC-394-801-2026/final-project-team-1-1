from django.contrib import admin

from pages.models import AppUser, Room, Asset, Log, Task, Consumable

admin.site.register(AppUser)
admin.site.register(Room)
admin.site.register(Asset)
admin.site.register(Task)
admin.site.register(Consumable)
admin.site.register(Log)
