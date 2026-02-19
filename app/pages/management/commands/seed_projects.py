from django.core.management.base import BaseCommand
from pages.models import DIYProject, ProjectStep
from datetime import timedelta
from django.db import transaction

class Command(BaseCommand):
    help = 'Seeds the database!!!!!!!!!!'

    def handle(self, *args, **options):
        projects_data = [
            {
                'title': 'Wooden Coffee Table',
                'description': 'asjdgbpaosdibgpaoiewgba',
                'avg_price': 50.00,
                'step_count': 5,
                'estimated_time': timedelta(hours=4),
                'is_rental_safe': True,
                'requires_drilling': True,
                'materials_json': ['wood ', 'screws', 'stain', 'sandpaper'],
                'tools_json': ['screwdriver'],
                'steps': [
                    'Cut to size',
                    'Sand surfaces',
                    'Assemble frame',
                    'Attach top',
                    'Apply stain'
                ]
            },
            {
                'title': 'Macrame Wall Thingy',
                'description': 'Eyesore wall hanging to decorate your bedroom.',
                'avg_price': 15.00,
                'step_count': 3,
                'estimated_time': timedelta(hours=2),
                'is_rental_safe': True,
                'requires_drilling': False,
                'materials_json': ['cotton ', 'dowel', 'scissors'],
                'tools_json': ['scissors'],
                'steps': [
                    'Cut twine',
                    'Tie twine on dowel',
                    'Create knot patterns',
                    'throw away'
                ]
            },
            {
                'title': 'Floating Shelves',
                'description': 'floating shelves that can\'t hold anything',
                'avg_price': 69.00,
                'step_count': 4,
                'estimated_time': timedelta(hours=3),
                'is_rental_safe': False,
                'requires_drilling': True,
                'materials_json': ['wood ', 'brackets', 'anchors', 'screws'],
                'tools_json': ['drill', 'screwdriver'],
                'steps': [
                    'Measure wall',
                    'Drill holes',
                    'Install brackets',
                    'Secure brackets'
                ]
            }
        ]

        # atomic, all or nothing so we don't insert something fucked up into the db. Modeling this off the ingest_data command I am making - james
        with transaction.atomic():
            for data in projects_data:
                # We have to remove the steps entirely from the project as it is going into a different but related model
                steps_data = data.pop('steps', [])
                project, created = DIYProject.objects.get_or_create(
                    title=data['title'],
                    defaults=data
                )

                #models what our ingest function would look like (how our project will ingest scrapped data)
                if created:
                    # btw, this takes the string in step_text and pairs it with the current i
                    for i, step_text in enumerate(steps_data, 1):
                        ProjectStep.objects.create(
                            project=project,
                            step_number=i,
                            instruction_text=step_text
                        )
                    self.stdout.write(self.style.SUCCESS(f'Created project: {project.title}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Project "{project.title}" already exists, skipping.'))

        self.stdout.write(self.style.SUCCESS('seeding done'))
