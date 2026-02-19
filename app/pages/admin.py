from django.contrib import admin
from .models import DIYProject, ProjectStep

# Gotta register the models with the admin site so we can mess with them
admin.site.register(DIYProject)
admin.site.register(ProjectStep)