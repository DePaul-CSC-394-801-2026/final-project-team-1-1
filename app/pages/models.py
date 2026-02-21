from django.core.validators import MinLengthValidator
from django.db import models


#User is parent model to others.
class AppUser(models.Model):
    username = models.CharField(
        primary_key=True,
        max_length=20,
        #Ensure uname is at least 5 characters
        validators=[MinLengthValidator(5)],
    )
    # Add email & pword fields
    email = models.EmailField(max_length=254)
    password = models.CharField(max_length=128)

    def __str__(self) -> str:
        return f"{self.username} ({self.email})"
