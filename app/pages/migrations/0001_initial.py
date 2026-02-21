from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AppUser",
            fields=[
                (
                    "username",
                    models.CharField(
                        max_length=20,
                        primary_key=True,
                        serialize=False,
                        validators=[django.core.validators.MinLengthValidator(5)],
                    ),
                ),
                ("password", models.CharField(max_length=128)),
            ],
        ),
    ]
