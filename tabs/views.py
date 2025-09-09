from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from decimal import Decimal
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Tab, MenuItem, TabItem
from .serializers import (
    CreateTabSerializer, TabSerializer, AddMenuItemSerializer, 
    TabItemSerializer, TabTotalsSerializer
)

class CreateTabView(APIView):
    @extend_schema(
        summary="Create a new tab",
        description="Create a new restaurant tab for a table",
        request=CreateTabSerializer,
        responses={
            201: TabSerializer,
        },
        examples=[
            OpenApiExample(
                'Create Tab Example',
                summary='Create tab for table 5',
                description='Create a new tab for table 5 with 2 covers',
                value={'table_number': 5, 'covers': 2}
            )
        ]
    )
    def post(self, request):
        serializer = CreateTabSerializer(data=request.data)
        if serializer.is_valid():
            tab = serializer.save()
            response_serializer = TabSerializer(tab)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetTabView(APIView):
    @extend_schema(
        summary="Get tab details",
        description="Retrieve detailed information about a specific tab including items and totals",
        parameters=[
            OpenApiParameter(
                name='tab_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Tab ID'
            )
        ],
        responses={
            200: TabSerializer,
        }
    )
    def get(self, request, tab_id):
        tab = get_object_or_404(Tab, id=tab_id)
        serializer = TabSerializer(tab)
        return Response(serializer.data)


class AddMenuItemView(APIView):
    @extend_schema(
        summary="Add menu item to tab",
        description="Add a menu item with quantity to an existing tab",
        request=AddMenuItemSerializer,
        responses={
            201: TabItemSerializer,
        },
        examples=[
            OpenApiExample(
                'Add Item Example',
                summary='Add 2 coffees to tab',
                description='Add 2 units of coffee (menu item ID 1) to the tab',
                value={'menu_item_id': 1, 'qty': 2}
            )
        ]
    )
    def post(self, request, tab_id):
        # Get the tab
        tab = get_object_or_404(Tab, id=tab_id)
        
        # Check if tab is open
        if tab.status != 'open':
            return Response({
                'error': 'Cannot add items to a closed or paid tab'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AddMenuItemSerializer(data=request.data)
        if serializer.is_valid():
            menu_item_id = serializer.validated_data['menu_item_id']
            qty = serializer.validated_data['qty']
            
            # Get the menu item
            menu_item = get_object_or_404(MenuItem, id=menu_item_id)
            
            # Calculate line totals
            line_subtotal_p = menu_item.unit_price_p * qty
            vat_p = int(Decimal(line_subtotal_p) * menu_item.vat_rate_percent / 100)
            line_total_p = line_subtotal_p + vat_p
            
            # Create the tab item
            tab_item = TabItem.objects.create(
                tab=tab,
                menu_item=menu_item,
                qty=qty,
                unit_price_p=menu_item.unit_price_p,
                vat_rate_percent=menu_item.vat_rate_percent,
                vat_p=vat_p,
                line_total_p=line_total_p
            )
            
            # Update tab totals
            update_tab_totals(tab)
            
            # Prepare response data
            response_data = TabItemSerializer(tab_item).data
            response_data['tab_totals'] = TabTotalsSerializer({
                'subtotal_p': tab.subtotal_p,
                'service_charge_p': tab.service_charge_p,
                'vat_total_p': tab.vat_total_p,
                'total_p': tab.total_p
            }).data
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def update_tab_totals(tab):
    """Update tab totals based on all tab items"""
    # Get all items for this tab
    tab_items = TabItem.objects.filter(tab=tab)
    
    # Calculate subtotal (sum of line totals minus VAT)
    subtotal_p = sum(item.line_total_p - item.vat_p for item in tab_items)
    
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