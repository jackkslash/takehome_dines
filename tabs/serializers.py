from rest_framework import serializers
from .models import Tab, MenuItem, TabItem
from decimal import Decimal


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'unit_price_p', 'vat_rate_percent']
        extra_kwargs = {
            'unit_price_p': {'help_text': 'Price in pence (e.g., 350 = £3.50)'},
            'vat_rate_percent': {'help_text': 'VAT rate as decimal (e.g., 20.0 for 20%)'}
        }


class TabItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    
    class Meta:
        model = TabItem
        fields = ['id', 'menu_item', 'menu_item_name', 'qty', 'unit_price_p', 
                 'vat_rate_percent', 'vat_p', 'line_total_p']
        extra_kwargs = {
            'vat_p': {'help_text': 'VAT amount in pence'},
            'line_total_p': {'help_text': 'Total line amount in pence (including VAT)'}
        }


class TabSerializer(serializers.ModelSerializer):
    items = TabItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Tab
        fields = ['id', 'table_number', 'covers', 'status', 'opened_at', 'closed_at',
                 'subtotal_p', 'service_charge_p', 'vat_total_p', 'total_p', 'items']
        read_only_fields = ['id', 'opened_at', 'closed_at', 'subtotal_p', 
                           'service_charge_p', 'vat_total_p', 'total_p', 'items']
        extra_kwargs = {
            'subtotal_p': {'help_text': 'Subtotal in pence (before VAT and service charge)'},
            'service_charge_p': {'help_text': 'Service charge in pence (10% of subtotal)'},
            'vat_total_p': {'help_text': 'Total VAT amount in pence'},
            'total_p': {'help_text': 'Final total in pence (subtotal + service charge + VAT)'}
        }


class CreateTabSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tab
        fields = ['table_number', 'covers']
        extra_kwargs = {
            'table_number': {'help_text': 'Table number (positive integer)'},
            'covers': {'help_text': 'Number of people (positive integer)'}
        }
    
    def validate_table_number(self, value):
        if value <= 0:
            raise serializers.ValidationError("table_number must be a positive integer")
        return value
    
    def validate_covers(self, value):
        if value <= 0:
            raise serializers.ValidationError("covers must be a positive integer")
        return value


class AddMenuItemSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField(help_text="ID of the menu item to add")
    qty = serializers.IntegerField(min_value=1, help_text="Quantity to add (minimum 1)")
    
    def validate_menu_item_id(self, value):
        try:
            MenuItem.objects.get(id=value)
        except MenuItem.DoesNotExist:
            raise serializers.ValidationError("Menu item not found")
        return value


class TabTotalsSerializer(serializers.Serializer):
    subtotal_p = serializers.IntegerField(help_text="Subtotal in pence")
    service_charge_p = serializers.IntegerField(help_text="Service charge in pence")
    vat_total_p = serializers.IntegerField(help_text="Total VAT in pence")
    total_p = serializers.IntegerField(help_text="Final total in pence")


def update_tab_totals(tab):
    """Update tab totals based on all tab items"""
    tab_items = TabItem.objects.filter(tab=tab)
    
    # Calculate subtotal (sum of line subtotals - BEFORE VAT)
    subtotal_p = sum((item.line_total_p - item.vat_p) for item in tab_items)
    
    # Calculate total VAT
    vat_total_p = sum(item.vat_p for item in tab_items)
    
    # Calculate service charge (10% of subtotal)
    service_charge_p = int(Decimal(subtotal_p) * Decimal('0.10'))
    
    # Calculate total
    total_p = subtotal_p + service_charge_p + vat_total_p
    
    # Update the tab
    tab.subtotal_p = subtotal_p
    tab.service_charge_p = service_charge_p
    tab.vat_total_p = vat_total_p
    tab.total_p = total_p
    tab.save()
