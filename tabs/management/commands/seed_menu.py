from django.core.management.base import BaseCommand
from tabs.models import MenuItem


class Command(BaseCommand):
    help = 'Seed the database with menu items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing menu items before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing menu items...')
            MenuItem.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS('Successfully cleared menu items')
            )

        # Create menu items
        menu_items = [
            {
                "name": "Flat White",
                "unit_price_p": 350,  # £3.50
                "vat_rate_percent": 20.0
            },
            {
                "name": "Croissant",
                "unit_price_p": 280,  # £2.80
                "vat_rate_percent": 20.0
            },
            {
                "name": "Iced Tea",
                "unit_price_p": 300,  # £3.00
                "vat_rate_percent": 20.0
            },
            {
                "name": "Kids Meal",
                "unit_price_p": 700,  # £7.00
                "vat_rate_percent": 5.0
            },
            {
                "name": "Pizza Margherita",
                "unit_price_p": 1200,  # £12.00
                "vat_rate_percent": 20.0
            },
            {
                "name": "Coca Cola",
                "unit_price_p": 300,  # £3.00
                "vat_rate_percent": 20.0
            },
            {
                "name": "Caesar Salad",
                "unit_price_p": 900,  # £9.00
                "vat_rate_percent": 20.0
            },
            {
                "name": "Chocolate Cake",
                "unit_price_p": 450,  # £4.50
                "vat_rate_percent": 20.0
            }
        ]

        # Create menu items
        created_items = []
        for item_data in menu_items:
            item, created = MenuItem.objects.get_or_create(
                name=item_data['name'],
                defaults={
                    'unit_price_p': item_data['unit_price_p'],
                    'vat_rate_percent': item_data['vat_rate_percent']
                }
            )
            if created:
                created_items.append(item)
                self.stdout.write(
                    f"Created: {item.name} - £{item.unit_price_p/100:.2f} (VAT: {item.vat_rate_percent}%)"
                )
            else:
                self.stdout.write(
                    f"Already exists: {item.name}"
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nTotal new menu items created: {len(created_items)}')
        )

        # Display all menu items
        self.stdout.write("\nAll menu items in database:")
        self.stdout.write("-" * 50)
        for item in MenuItem.objects.all().order_by('name'):
            self.stdout.write(
                f"ID: {item.id:2d} | {item.name:20s} | £{item.unit_price_p/100:6.2f} | VAT: {item.vat_rate_percent:4.1f}%"
            )
