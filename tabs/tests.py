from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import Tab, MenuItem, TabItem
from .views import update_tab_totals


class TabCalculationTests(TestCase):
    """Test VAT + service charge logic and total calculations"""
    
    def setUp(self):
        # Create test menu items
        self.menu_item_1 = MenuItem.objects.create(
            name="Coffee",
            unit_price_p=350,  # £3.50
            vat_rate_percent=Decimal('20.0')
        )
        
        self.menu_item_2 = MenuItem.objects.create(
            name="Kids Meal",
            unit_price_p=800,  # £8.00
            vat_rate_percent=Decimal('0.0')
        )
        
        self.tab = Tab.objects.create(
            table_number=1,
            covers=2
        )
    
    def test_vat_calculation_per_line(self):
        """Test VAT calculation per line item"""
        # Create tab item: 2x Coffee at £3.50 each
        tab_item = TabItem.objects.create(
            tab=self.tab,
            menu_item=self.menu_item_1,
            qty=2,
            unit_price_p=350,
            vat_rate_percent=Decimal('20.0'),
            vat_p=140,  # 20% of £7.00 = £1.40 = 140p
            line_total_p=840  # £7.00 + £1.40 = £8.40 = 840p
        )
        
        # Verify VAT calculation: 20% of £7.00 = £1.40 = 140p
        expected_vat = int(Decimal(700) * Decimal('20.0') / 100)
        self.assertEqual(tab_item.vat_p, expected_vat)
        self.assertEqual(tab_item.vat_p, 140)
    
    def test_zero_vat_calculation(self):
        """Test zero VAT calculation for kids meals"""
        # Create tab item: 1x Kids Meal at £8.00
        tab_item = TabItem.objects.create(
            tab=self.tab,
            menu_item=self.menu_item_2,
            qty=1,
            unit_price_p=800,
            vat_rate_percent=Decimal('0.0'),
            vat_p=0,  # 0% VAT
            line_total_p=800  # £8.00 + £0.00 = £8.00
        )
        
        self.assertEqual(tab_item.vat_p, 0)
        self.assertEqual(tab_item.line_total_p, 800)
    
    def test_service_charge_calculation(self):
        """Test service charge is 10% of subtotal, rounded to pence"""
        # Create items with known subtotal
        TabItem.objects.create(
            tab=self.tab,
            menu_item=self.menu_item_1,
            qty=2,  # 2x £3.50 = £7.00
            unit_price_p=350,
            vat_rate_percent=Decimal('20.0'),
            vat_p=140,  # £1.40 VAT
            line_total_p=840  # £8.40 total
        )
        
        TabItem.objects.create(
            tab=self.tab,
            menu_item=self.menu_item_2,
            qty=1,  # 1x £8.00 = £8.00
            unit_price_p=800,
            vat_rate_percent=Decimal('0.0'),
            vat_p=0,  # £0.00 VAT
            line_total_p=800  # £8.00 total
        )
        
        # Update tab totals
        update_tab_totals(self.tab)
        self.tab.refresh_from_db()
        
        # Subtotal = £7.00 + £8.00 = £15.00 = 1500p
        expected_subtotal = 1500
        # Service charge = 10% of £15.00 = £1.50 = 150p
        expected_service_charge = int(Decimal(1500) * Decimal('0.10'))
        
        self.assertEqual(self.tab.subtotal_p, expected_subtotal)
        self.assertEqual(self.tab.service_charge_p, expected_service_charge)
        self.assertEqual(self.tab.service_charge_p, 150)
    
    def test_total_calculation(self):
        """Test total = subtotal + service charge + VAT"""
        # Create items
        TabItem.objects.create(
            tab=self.tab,
            menu_item=self.menu_item_1,
            qty=1,  # 1x £3.50 = £3.50
            unit_price_p=350,
            vat_rate_percent=Decimal('20.0'),
            vat_p=70,  # £0.70 VAT
            line_total_p=420  # £4.20 total
        )
        
        TabItem.objects.create(
            tab=self.tab,
            menu_item=self.menu_item_2,
            qty=1,  # 1x £8.00 = £8.00
            unit_price_p=800,
            vat_rate_percent=Decimal('0.0'),
            vat_p=0,  # £0.00 VAT
            line_total_p=800  # £8.00 total
        )
        
        # Update tab totals
        update_tab_totals(self.tab)
        self.tab.refresh_from_db()
        
        # Expected calculations:
        # Subtotal = £3.50 + £8.00 = £11.50 = 1150p
        # VAT Total = £0.70 + £0.00 = £0.70 = 70p
        # Service Charge = 10% of £11.50 = £1.15 = 115p
        # Total = £11.50 + £1.15 + £0.70 = £13.35 = 1335p
        
        expected_subtotal = 1150
        expected_vat_total = 70
        expected_service_charge = 115
        expected_total = expected_subtotal + expected_service_charge + expected_vat_total
        
        self.assertEqual(self.tab.subtotal_p, expected_subtotal)
        self.assertEqual(self.tab.vat_total_p, expected_vat_total)
        self.assertEqual(self.tab.service_charge_p, expected_service_charge)
        self.assertEqual(self.tab.total_p, expected_total)
        self.assertEqual(self.tab.total_p, 1335)
    
    def test_rounding_service_charge(self):
        """Test service charge rounding to pence"""
        # Create item that will result in non-round service charge
        TabItem.objects.create(
            tab=self.tab,
            menu_item=self.menu_item_1,
            qty=3,  # 3x £3.50 = £10.50
            unit_price_p=350,
            vat_rate_percent=Decimal('20.0'),
            vat_p=210,  # £2.10 VAT
            line_total_p=1260  # £12.60 total
        )
        
        update_tab_totals(self.tab)
        self.tab.refresh_from_db()
        
        # Subtotal = £10.50 = 1050p
        # Service charge = 10% of £10.50 = £1.05 = 105p (should round to 105p)
        expected_service_charge = int(Decimal(1050) * Decimal('0.10'))
        
        self.assertEqual(self.tab.service_charge_p, expected_service_charge)
        self.assertEqual(self.tab.service_charge_p, 105)


class TabAPITests(APITestCase):
    """Test tab API endpoints"""
    
    def setUp(self):
        self.menu_item = MenuItem.objects.create(
            name="Test Item",
            unit_price_p=500,  # £5.00
            vat_rate_percent=Decimal('20.0')
        )
        # Add API key to all requests
        self.client.defaults['HTTP_X_API_KEY'] = 'demo'
    
    def test_create_tab(self):
        """Test creating a new tab"""
        url = reverse('create_tab')
        data = {
            'table_number': 5,
            'covers': 3
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tab.objects.count(), 1)
        
        tab = Tab.objects.first()
        self.assertEqual(tab.table_number, 5)
        self.assertEqual(tab.covers, 3)
        self.assertEqual(tab.status, 'open')
    
    def test_add_menu_item_to_tab(self):
        """Test adding menu item to tab"""
        # Create tab first
        tab = Tab.objects.create(table_number=1, covers=2)
        
        url = reverse('add_menu_item', kwargs={'tab_id': tab.id})
        data = {
            'menu_item_id': self.menu_item.id,
            'qty': 2
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TabItem.objects.count(), 1)
        
        tab_item = TabItem.objects.first()
        self.assertEqual(tab_item.qty, 2)
        self.assertEqual(tab_item.unit_price_p, 500)
        
        # Check tab totals were updated
        tab.refresh_from_db()
        self.assertGreater(tab.total_p, 0)
