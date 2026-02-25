from django.core.management.base import BaseCommand
from pages.models import AssetDetails


# This file is responsible for bulk importing AssetDetails
# To add more data, add another line below
# Make sure to ALWAYS leave owner as null. That's how the backend knows it's not a user created object
# TODO: Import consumables for assets that have them
# To run, do docker compose exec app python app/manage.py load_assets
class Command(BaseCommand):
    help = 'Load initial asset data'

    def handle(self, *args, **options):
        AssetDetails.objects.get_or_create(name="Under Sink Water Filter", brand="GE", model_number="GXK140TNN", owner=None)
        AssetDetails.objects.get_or_create(name="50-Pint Dehumifier", brand="GE", model_number="APHL50LB", owner=None)
        AssetDetails.objects.get_or_create(name="PLUS Faucet Mount Filtration System", brand="PUR", model_number="PFM400H", owner=None)
        AssetDetails.objects.get_or_create(name="Side-By-Side Refridgerator", brand="Frigidaire", model_number="FRSS2623AS", owner=None)
        AssetDetails.objects.get_or_create(name="5 Burner Electric Range", brand="Frigidaire", model_number="FCRE3052BS", owner=None)
        AssetDetails.objects.get_or_create(name="Front Control Smart Dishwasher", brand="Frigidaire", model_number="FDPC4221AS", owner=None)
        AssetDetails.objects.get_or_create(name="Top Control Dishwasher", brand="Frigidaire", model_number="FDPH4316AS", owner=None)
        AssetDetails.objects.get_or_create(name="Smart Front Load Washer", brand="LG", model_number="WM4000HBA", owner=None)

        self.stdout.write(self.style.SUCCESS("Assets loaded successfully"))