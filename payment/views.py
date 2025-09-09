from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from tabs.models import Tab
from .models import Payment
from .serializers import PaymentSerializer, CreatePaymentIntentSerializer, TakePaymentSerializer
from .gateway import MockPaymentGateway


# Create your views here.


class CreatePaymentIntentView(APIView):
    """Create a payment intent for a tab"""
    
    @extend_schema(
        summary="Create payment intent",
        description="Create a payment intent for a tab. Returns a client_secret for payment processing.",
        request=CreatePaymentIntentSerializer,
        responses={
            200: PaymentSerializer
        },
        examples=[
            OpenApiExample(
                'Payment Intent Response',
                summary='Successful payment intent creation',
                description='Response when payment intent is created successfully',
                value={
                    'client_secret': 'secret_abc123',
                    'status': 'requires_confirmation',
                    'amount_p': 1335,
                    'currency': 'gbp'
                }
            )
        ]
    )
    def post(self, request, tab_id):
        # Get the tab
        tab = get_object_or_404(Tab, id=tab_id)
        
        # Check if tab is closed or paid
        if tab.status in ['closed', 'paid']:
            return Response({
                'error': 'Cannot create payment intent for closed or paid tab'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if tab has items
        if not tab.items.exists():
            return Response({
                'error': 'Cannot create payment intent for empty tab'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if payment intent already exists for this tab
        existing_payment = Payment.objects.filter(tab=tab, status='requires_confirmation').first()
        if existing_payment:
            # Get the client_secret from Redis
            gateway = MockPaymentGateway()
            client_secret = gateway.get_client_secret_from_intent_id(existing_payment.payment_intent_id)
            if client_secret:
                return Response({
                    'client_secret': client_secret,
                    'status': existing_payment.status,
                    'amount_p': existing_payment.amount_p,
                    'currency': existing_payment.currency
                }, status=status.HTTP_200_OK)
        
        # Create payment intent using mock gateway
        gateway = MockPaymentGateway()
        intent_data = gateway.create_payment_intent(amount_p=tab.total_p)
        
        # Store payment record in database (only intent_id, not client_secret)
        payment = Payment.objects.create(
            tab=tab,
            payment_intent_id=intent_data['intent_id'],  # Internal ID only
            amount_p=intent_data['amount'],
            currency=intent_data['currency'],
            status=intent_data['status']
        )
        
        # Store the mapping in Redis: client_secret -> intent_id
        gateway.store_secret_mapping(
            client_secret=intent_data['client_secret'],
            intent_id=intent_data['intent_id']
        )
        
        # Return payment intent data to user
        return Response({
            'client_secret': intent_data['client_secret'],
            'status': intent_data['status'],
            'amount_p': intent_data['amount'],
            'currency': intent_data['currency']
        }, status=status.HTTP_201_CREATED)


class TakePaymentView(APIView):
    """Take payment (confirm payment intent)"""
    
    @extend_schema(
        summary="Take payment",
        description="Process payment using client_secret. Idempotent operation.",
        request=TakePaymentSerializer,
        parameters=[
            OpenApiParameter(
                name='tab_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Tab ID'
            )
        ],
        responses={
            200: PaymentSerializer,
            400: OpenApiTypes.OBJECT,
            402: OpenApiTypes.OBJECT
        },
        examples=[
            OpenApiExample(
                'Payment Request',
                summary='Payment request body',
                description='Request body for taking payment',
                value={'client_secret': 'secret_abc123'}
            ),
            OpenApiExample(
                'Payment Success',
                summary='Successful payment',
                description='Response when payment is processed successfully',
                value={
                    'status': 'succeeded',
                    'amount_p': 1335,
                    'currency': 'gbp',
                    'confirmed_at': '2024-01-01T12:00:00Z'
                }
            ),
            OpenApiExample(
                'Payment Failure',
                summary='Failed payment',
                description='Response when payment fails (e.g., amount ends in 13)',
                value={
                    'error': 'Payment failed',
                    'reason': 'Insufficient funds'
                }
            )
        ]
    )
    def post(self, request, tab_id):
        # Get the tab
        tab = get_object_or_404(Tab, id=tab_id)
        
        # Validate request data
        serializer = TakePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        client_secret = serializer.validated_data['client_secret']
        
        # Get the intent_id from Redis using client_secret
        gateway = MockPaymentGateway()
        intent_id = gateway.get_intent_id_from_secret(client_secret)
        
        if not intent_id:
            return Response({
                'error': 'Payment intent not found or expired'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the payment record from database using intent_id
        payment = get_object_or_404(Payment, payment_intent_id=intent_id, tab=tab)
        
        # Check if payment is already confirmed (idempotency check)
        if payment.status == 'succeeded':
            # Idempotent: return success if already paid
            return Response({
                'status': payment.status,
                'amount_p': payment.amount_p,
                'currency': payment.currency,
                'confirmed_at': payment.confirmed_at
            }, status=status.HTTP_200_OK)
        
        if payment.status == 'failed':
            return Response({
                'error': 'Payment has already failed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Confirm payment using intent_id
        confirmation_data = gateway.confirm_payment_intent(intent_id, payment.amount_p)
        
        # Update payment status
        payment.status = confirmation_data['status']
        payment.confirmed_at = timezone.now()
        
        if confirmation_data['status'] == 'failed':
            payment.failure_reason = confirmation_data.get('reason', 'Payment failed')
            payment.save()
            
            # Clean up Redis mapping on failure
            gateway.cleanup_secret_mapping(client_secret)
            
            return Response({
                'error': 'Payment failed',
                'reason': payment.failure_reason
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        # Payment succeeded
        payment.save()
        
        # Update tab status
        tab.status = 'paid'
        tab.closed_at = timezone.now()
        tab.save()
        
        # DON'T clean up Redis mapping immediately - keep it for idempotency
        # The mapping will expire naturally after 15 minutes
        
        return Response({
            'status': payment.status,
            'amount_p': payment.amount_p,
            'currency': payment.currency,
            'confirmed_at': payment.confirmed_at
        }, status=status.HTTP_200_OK)
