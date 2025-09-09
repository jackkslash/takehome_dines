from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'amount_p', 'currency', 'status', 
                 'failure_reason', 'created_at', 'confirmed_at']
        read_only_fields = ['id', 'created_at', 'confirmed_at']


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating payment intent (no additional fields needed)"""
    pass


class TakePaymentSerializer(serializers.Serializer):
    """Serializer for taking payment"""
    client_secret = serializers.CharField(
        max_length=100,
        help_text="Client secret from payment intent creation"
    )
