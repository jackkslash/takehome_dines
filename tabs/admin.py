from django.contrib import admin
from .models import MenuItem, Tab, TabItem

# Register your models here.
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['id','name', 'unit_price_p', 'vat_rate_percent']
    search_fields = ['name']
    list_filter = ['vat_rate_percent']

@admin.register(Tab)
class TabAdmin(admin.ModelAdmin):
    list_display = ['id', 'table_number', 'covers', 'status', 'opened_at', 'total_p']
    list_filter = ['status', 'opened_at']
    search_fields = ['table_number']
    readonly_fields = ['opened_at', 'closed_at']

@admin.register(TabItem)
class TabItemAdmin(admin.ModelAdmin):
    list_display = ['tab', 'menu_item', 'qty', 'unit_price_p', 'line_total_p']
    list_filter = ['tab__status', 'menu_item']
    search_fields = ['tab__table_number', 'menu_item__name']
