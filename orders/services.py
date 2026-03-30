from typing import Any, Dict, List
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import Order, OrderItem
from marketplace.models import Product
from vendors.models import Vendor
from hostels.models import Hostel
from accounts.models import User
from decimal import Decimal

class OrderService:
    @staticmethod
    def _validate_hostel_owner(user: User, hostel_id: int) -> Hostel:
        """
        Verify that the user owns the hostel they are ordering for.
        """
        try:
            hostel = Hostel.objects.get(id=hostel_id, owner=user)
            return hostel
        except Hostel.DoesNotExist:
            raise PermissionDenied("You do not own this hostel or it does not exist.")

    @staticmethod
    @transaction.atomic
    def create_structured_order(user: User, data: Dict[str, Any]) -> Order:
        """
        Business logic for creating a catalog-based structured order.
        """
        hostel = OrderService._validate_hostel_owner(user, data['hostel_id'])
        
        try:
            vendor = Vendor.objects.get(id=data['vendor_id'], is_active=True)
        except Vendor.DoesNotExist:
            raise ValidationError("Vendor is inactive or doesn't exist.")

        order = Order.objects.create(
            hostel=hostel,
            vendor=vendor,
            order_type=Order.OrderType.STRUCTURED,
            status=Order.StatusChoices.PENDING,
            note=data.get('note', '')
        )

        total_order_amount = Decimal('0.00')
        items_data = data.get('items', [])
        
        if not items_data:
            raise ValidationError("Structured orders must contain items.")

        for item in items_data:
            try:
                product = Product.objects.get(
                    id=item['product_id'], 
                    vendor=vendor, 
                    is_available=True
                )
            except Product.DoesNotExist:
                raise ValidationError(f"Product ID {item['product_id']} is unavailable or doesn't belong to this vendor.")

            total_item_price = product.price * item['quantity']
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name_at_order=product.name,
                quantity=item['quantity'],
                unit_price=product.price,
                total_price=total_item_price
            )
            total_order_amount += total_item_price

        order.total_amount = total_order_amount
        order.save()
        return order

    @staticmethod
    def create_image_scan_order(user: User, data: Dict[str, Any]) -> Order:
        """
        Business logic for creating an image-based list order.
        """
        hostel = OrderService._validate_hostel_owner(user, data['hostel_id'])
        
        try:
            vendor = Vendor.objects.get(id=data['vendor_id'], is_active=True)
        except Vendor.DoesNotExist:
            raise ValidationError("Vendor is inactive or doesn't exist.")

        order = Order.objects.create(
            hostel=hostel,
            vendor=vendor,
            order_type=Order.OrderType.IMAGE_SCAN,
            status=Order.StatusChoices.PENDING,
            scan_image=data.get('scan_image'),
            note=data.get('note', '')
        )
        return order

    @staticmethod
    def update_order_status(user: User, order: Order, new_status: str) -> Order:
        """
        Verify that only vendors can update statuses of orders they received.
        """
        if order.vendor.owner != user:
            raise PermissionDenied("Only the managing vendor can update this order status.")
        
        if new_status not in Order.StatusChoices.values:
            raise ValidationError("Invalid order status.")
            
        order.status = new_status
        order.save()
        return order

    @staticmethod
    def list_orders_for_user(user: User):
        """
        Optimization: use select_related and prefetch_related based on role.
        """
        if user.role == "hostel_owner":
            return Order.objects.filter(hostel__owner=user).select_related('vendor', 'hostel').prefetch_related('items')
        elif user.role == "vendor":
            return Order.objects.filter(vendor__owner=user).select_related('vendor', 'hostel').prefetch_related('items')
        else:
            return Order.objects.none()
