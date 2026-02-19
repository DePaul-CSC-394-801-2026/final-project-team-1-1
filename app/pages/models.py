import uuid

from django.db import models

# Definitely not concrete!!! These attributes are just what I landed on per our demo stuff
# I think, if we find an AI scraper, we could give it this model and tell it to figure it out, for the normalization? So we don't have to fine-tune something more manually.
class DIYProject(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    avg_price = models.DecimalField(max_digits=10, decimal_places=2)
    step_count = models.IntegerField()
    estimated_time = models.DurationField() #Could be a problem with this field type
    is_rental_safe = models.BooleanField(default=True)
    requires_drilling = models.BooleanField(default=False)
    materials_json = models.JSONField() # Could be a problem with this field type too
    tools_json = models.JSONField(default=list)

    def __str__(self):
        return self.title

# One project has many steps. This model is so we can better formalize the difficulty thing we want to do? Defining a
# model to handle project steps will allow for more structured and organized project instructions from the various
# sources we fetch from.
class ProjectStep(models.Model):
    project = models.ForeignKey(
        DIYProject,
        related_name='steps',
        on_delete=models.CASCADE
    )
    step_number = models.PositiveIntegerField()
    instruction_text = models.TextField()

    class Meta:
        ordering = ['step_number'] # Keeps them in order automatically

    def __str__(self):
        return f"Step {self.step_number} for {self.project.title}"