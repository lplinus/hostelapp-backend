from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Order
from .serializers import (
    OrderSerializer, 
    OrderItemSerializer, 
    StructuredOrderCreateSerializer, 
    ImageScanOrderCreateSerializer
)
from .services import OrderService

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Thin ViewSet to handle user-specific orders.
    Delegates complex creation and status updates to OrderService.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Efficient, role-based order listing.
        """
        return OrderService.list_orders_for_user(self.request.user)

    @action(detail=False, methods=['post'], url_path='create-structured')
    def create_structured(self, request):
        """
        Action for catalog-based orders.
        """
        serializer = StructuredOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            order = OrderService.create_structured_order(
                user=request.user, 
                data=serializer.validated_data
            )
            return Response({
                "success": True,
                "message": "Structured order placed successfully.",
                "data": OrderSerializer(order).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='create-image-scan')
    def create_image_scan(self, request):
        """
        Action for image-based handwritten list orders.
        """
        serializer = ImageScanOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            order = OrderService.create_image_scan_order(
                user=request.user, 
                data=serializer.validated_data
            )
            return Response({
                "success": True,
                "message": "Image scan order uploaded successfully.",
                "data": OrderSerializer(order).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Action for vendors to transition order states.
        """
        order = self.get_object()
        new_status = request.data.get('status')
        
        try:
            updated_order = OrderService.update_order_status(
                user=request.user, 
                order=order, 
                new_status=new_status
            )
            return Response({
                "success": True,
                "message": f"Order status updated to {new_status}.",
                "data": OrderSerializer(updated_order).data
            })
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
