from django.contrib import admin
from .models import Payment

# Register your models here.
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'tab', 'payment_intent_id', 'amount_p', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['payment_intent_id', 'tab__table_number']
    readonly_fields = ['created_at']
