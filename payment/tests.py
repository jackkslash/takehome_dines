from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from tabs.models import Tab, MenuItem, TabItem
from .models import Payment
from .gateway import MockPaymentGateway
from decimal import Decimal


class PaymentGatewayTests(TestCase):
    """Test mock payment gateway functionality"""
    
    def setUp(self):
        self.gateway = MockPaymentGateway()
    
    def test_create_payment_intent(self):
        """Test creating a payment intent"""
        result = self.gateway.create_payment_intent(amount_p=1000, currency="gbp")
        
        self.assertIn('intent_id', result)
        self.assertIn('client_secret', result)
        self.assertEqual(result['amount'], 1000)
        self.assertEqual(result['currency'], 'gbp')
        self.assertEqual(result['status'], 'requires_confirmation')
    
    def test_payment_success(self):
        """Test successful payment confirmation"""
        result = self.gateway.confirm_payment_intent("pi_test123", 1000)
        
        self.assertEqual(result['status'], 'succeeded')
    
    def test_payment_failure_amount_ends_in_13(self):
        """Test payment failure when amount ends in 13"""
        # Test amounts ending in 13
        test_amounts = [113, 213, 1013, 2013]
        
        for amount in test_amounts:
            result = self.gateway.confirm_payment_intent("pi_test123", amount)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['reason'], 'Insufficient funds')
    
    def test_payment_success_amount_not_ending_in_13(self):
        """Test payment success when amount doesn't end in 13"""
        # Test amounts not ending in 13
        test_amounts = [100, 200, 1000, 2000, 1012, 2014]
        
        for amount in test_amounts:
            result = self.gateway.confirm_payment_intent("pi_test123", amount)
            self.assertEqual(result['status'], 'succeeded')
    
    def test_redis_secret_mapping(self):
        """Test Redis secret mapping functionality"""
        client_secret = "secret_test123"
        intent_id = "pi_test123"
        
        # Store mapping
        result = self.gateway.store_secret_mapping(client_secret, intent_id)
        self.assertTrue(result)
        
        # Retrieve mapping
        retrieved_intent_id = self.gateway.get_intent_id_from_secret(client_secret)
        self.assertEqual(retrieved_intent_id, intent_id)
        
        # Cleanup
        cleanup_result = self.gateway.cleanup_secret_mapping(client_secret)
        self.assertTrue(cleanup_result)
        
        # Verify cleanup
        retrieved_after_cleanup = self.gateway.get_intent_id_from_secret(client_secret)
        self.assertIsNone(retrieved_after_cleanup)


class PaymentAPITests(APITestCase):
    """Test payment API endpoints"""
    
    def setUp(self):
        # Create test data
        self.menu_item = MenuItem.objects.create(
            name="Test Item",
            unit_price_p=500,  # £5.00
            vat_rate_percent=Decimal('20.0')
        )
        
        self.tab = Tab.objects.create(table_number=1, covers=2)
        # Add API key to all requests
        self.client.defaults['HTTP_X_API_KEY'] = 'demo'
        
        # Add item to tab
        TabItem.objects.create(
            tab=self.tab,
            menu_item=self.menu_item,
            qty=2,
            unit_price_p=500,
            vat_rate_percent=Decimal('20.0'),
            vat_p=200,  # £2.00 VAT
            line_total_p=1200  # £12.00 total
        )
        
        # Update tab totals
        from tabs.views import update_tab_totals
        update_tab_totals(self.tab)
    
    def test_create_payment_intent(self):
        """Test creating a payment intent"""
        url = reverse('create_payment_intent', kwargs={'tab_id': self.tab.id})
        
        response = self.client.post(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 1)
        
        payment = Payment.objects.first()
        self.assertEqual(payment.tab, self.tab)
        self.assertEqual(payment.amount_p, self.tab.total_p)
        self.assertEqual(payment.status, 'requires_confirmation')
        
        # Check response contains required fields
        self.assertIn('client_secret', response.data)
        self.assertIn('status', response.data)
        self.assertIn('amount_p', response.data)
        self.assertIn('currency', response.data)
    
    def test_take_payment_success(self):
        """Test successful payment"""
        # Create payment intent first
        url = reverse('create_payment_intent', kwargs={'tab_id': self.tab.id})
        response = self.client.post(url, {}, format='json')
        client_secret = response.data['client_secret']
        
        # Take payment (with amount that doesn't end in 13)
        url = reverse('take_payment', kwargs={'tab_id': self.tab.id})
        data = {'client_secret': client_secret}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check payment status
        payment = Payment.objects.first()
        self.assertEqual(payment.status, 'succeeded')
        self.assertIsNotNone(payment.confirmed_at)
        
        # Check tab status
        self.tab.refresh_from_db()
        self.assertEqual(self.tab.status, 'paid')
        self.assertIsNotNone(self.tab.closed_at)
        
        # Check response doesn't contain client_secret or IDs
        self.assertNotIn('client_secret', response.data)
        self.assertNotIn('id', response.data)
        self.assertNotIn('intent_id', response.data)
    
    def test_take_payment_failure(self):
        """Test payment failure when amount ends in 13"""
        # Create payment intent first
        url = reverse('create_payment_intent', kwargs={'tab_id': self.tab.id})
        response = self.client.post(url, {}, format='json')
        client_secret = response.data['client_secret']
        
        # Manually set amount to end in 13 for testing
        payment = Payment.objects.first()
        payment.amount_p = 1013  # Amount ending in 13
        payment.save()
        
        # Take payment
        url = reverse('take_payment', kwargs={'tab_id': self.tab.id})
        data = {'client_secret': client_secret}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertIn('error', response.data)
        self.assertIn('reason', response.data)
        
        # Check payment status
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'failed')
        self.assertIsNotNone(payment.failure_reason)
        
        # Check tab remains open
        self.tab.refresh_from_db()
        self.assertEqual(self.tab.status, 'open')
    
    def test_take_payment_idempotency(self):
        """Test take_payment idempotency"""
        # Create payment intent first
        url = reverse('create_payment_intent', kwargs={'tab_id': self.tab.id})
        response = self.client.post(url, {}, format='json')
        client_secret = response.data['client_secret']
        
        # Take payment first time
        url = reverse('take_payment', kwargs={'tab_id': self.tab.id})
        data = {'client_secret': client_secret}
        
        response1 = self.client.post(url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Take payment second time (should be idempotent)
        response2 = self.client.post(url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Both responses should be identical
        self.assertEqual(response1.data, response2.data)
        
        # Only one payment record should exist
        self.assertEqual(Payment.objects.count(), 1)
        
        # Tab should be paid
        self.tab.refresh_from_db()
        self.assertEqual(self.tab.status, 'paid')
    
    def test_take_payment_invalid_secret(self):
        """Test taking payment with invalid client secret"""
        url = reverse('take_payment', kwargs={'tab_id': self.tab.id})
        data = {'client_secret': 'invalid_secret'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class EndToEndPaymentTests(APITestCase):
    """End-to-end payment flow tests"""
    
    def setUp(self):
        # Create menu items
        self.coffee = MenuItem.objects.create(
            name="Coffee",
            unit_price_p=350,  # £3.50
            vat_rate_percent=Decimal('20.0')
        )
        
        self.croissant = MenuItem.objects.create(
            name="Croissant",
            unit_price_p=250,  # £2.50
            vat_rate_percent=Decimal('20.0')
        )
        # Add API key to all requests
        self.client.defaults['HTTP_X_API_KEY'] = 'demo'
    
    def test_complete_payment_flow(self):
        """Test complete flow: Open tab → Add items → Create payment intent → Take payment"""
        
        # Step 1: Create tab
        url = reverse('create_tab')
        data = {'table_number': 5, 'covers': 2}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tab_id = response.data['id']
        
        # Step 2: Add items to tab
        url = reverse('add_menu_item', kwargs={'tab_id': tab_id})
        
        # Add coffee
        data = {'menu_item_id': self.coffee.id, 'qty': 2}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Add croissant
        data = {'menu_item_id': self.croissant.id, 'qty': 1}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 3: Get tab details to verify totals
        url = reverse('get_tab', kwargs={'tab_id': tab_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        tab_data = response.data
        self.assertEqual(len(tab_data['items']), 2)
        self.assertGreater(tab_data['total_p'], 0)
        
        # Step 4: Create payment intent
        url = reverse('create_payment_intent', kwargs={'tab_id': tab_id})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        client_secret = response.data['client_secret']
        self.assertIsNotNone(client_secret)
        
        # Step 5: Take payment
        url = reverse('take_payment', kwargs={'tab_id': tab_id})
        data = {'client_secret': client_secret}
        response = self.client.post(url, data, format='json')
        
        # Payment should succeed (unless amount ends in 13)
        if response.status_code == status.HTTP_200_OK:
            # Payment succeeded
            self.assertEqual(response.data['status'], 'succeeded')
            
            # Verify tab is paid
            url = reverse('get_tab', kwargs={'tab_id': tab_id})
            response = self.client.get(url)
            self.assertEqual(response.data['status'], 'paid')
            self.assertIsNotNone(response.data['closed_at'])
        else:
            # Payment failed (amount ended in 13)
            self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
            self.assertIn('error', response.data)
            
            # Verify tab remains open
            url = reverse('get_tab', kwargs={'tab_id': tab_id})
            response = self.client.get(url)
            self.assertEqual(response.data['status'], 'open')
