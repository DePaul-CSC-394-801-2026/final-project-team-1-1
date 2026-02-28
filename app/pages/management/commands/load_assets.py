from django.core.management.base import BaseCommand
"""
No longer used command. AssetDetails were removed in favor of a single Asset model.
Keep this command as a no-op i guess
"""
class Command(BaseCommand):
    help = 'Load initial asset data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("This deosn't do anything anymore"))
