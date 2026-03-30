from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Vendor
from marketplace.models import Product
from .serializers import VendorSerializer, VendorDetailSerializer, ProductSerializer
from .services import VendorService

class VendorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vendor profiles and viewing vendors in marketplace.
    """
    queryset = Vendor.objects.all().select_related('owner')
    serializer_class = VendorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['business_name', 'description']
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'marketplace_detail']:
            return VendorDetailSerializer
        return VendorSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'marketplace']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """
        Custom create to use the Service layer.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            vendor = VendorService.create_vendor(
                owner=request.user, 
                data=serializer.validated_data
            )
            response_serializer = VendorSerializer(vendor)
            return Response({
                "success": True,
                "message": "Vendor profile created successfully.",
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='marketplace')
    def marketplace(self, request):
        """
        Custom action for public vendor listings.
        """
        search = request.query_params.get('search')
        vendors = VendorService.list_public_vendors(search=search)
        page = self.paginate_queryset(vendors)
        if page is not None:
            serializer = VendorSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = VendorSerializer(vendors, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        })

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get the current user's vendor profile.
        """
        try:
            vendor = Vendor.objects.get(owner=request.user)
            serializer = VendorSerializer(vendor)
            return Response(serializer.data)
        except Vendor.DoesNotExist:
            return Response({"error": "No vendor profile found for this user."}, status=status.HTTP_404_NOT_FOUND)

class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for vendors to manage their product catalog.
    """
    queryset = Product.objects.all().select_related('vendor')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Product.objects.all()
        return Product.objects.filter(vendor__owner=user)

    def perform_create(self, serializer):
        try:
            vendor = Vendor.objects.get(owner=self.request.user)
            serializer.save(vendor=vendor)
        except Vendor.DoesNotExist:
            raise Response({"error": "No vendor profile found."}, status=status.HTTP_400_BAD_REQUEST)
