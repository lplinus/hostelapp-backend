from django.db import models
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer, ProductCreateUpdateSerializer
from .services import MarketplaceService
from vendors.models import Vendor

class CategoryViewSet(viewsets.ModelViewSet):
    """
    Manage and view product categories.
    """
    queryset = Category.objects.filter(is_active=True).prefetch_related('subcategories')
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'with_counts']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['get'], url_path='with-counts')
    def with_counts(self, request):
        """
        Get categories with active product counts.
        """
        categories = MarketplaceService.get_active_categories_with_counts()
        serializer = self.get_serializer(categories, many=True)
        # Add the annotation to the data
        data = serializer.data
        for i, obj in enumerate(categories):
            data[i]['product_count'] = obj.product_count
        
        return Response({
            "success": True,
            "data": data
        })

class ProductViewSet(viewsets.ModelViewSet):
    """
    Discovery and management of marketplace products.
    """
    def get_queryset(self):
        queryset = Product.objects.all().select_related('vendor', 'category')
        user = self.request.user
        
        # Check if specifically requesting personal items
        mine = self.request.query_params.get('mine', 'false').lower() == 'true'
        
        if user.is_authenticated:
            try:
                vendor = Vendor.objects.get(owner=user)
                if mine:
                    # Dashboard view: Only see own products
                    return queryset.filter(vendor=vendor)
                
                # Discovery view: See own products (even inactive) + active products from others
                return queryset.filter(models.Q(vendor=vendor) | models.Q(is_active=True))
            except Vendor.DoesNotExist:
                pass
        
        # Everyone else only sees active products
        return queryset.filter(is_active=True)

    serializer_class = ProductSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'vendor', 'is_featured']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'stock']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'catalog', 'featured']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """
        Vendors use this to add themselves to the marketplace catalog.
        """
        serializer = ProductCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            vendor = Vendor.objects.get(owner=request.user)
            product = MarketplaceService.add_product_to_marketplace(
                vendor=vendor, 
                data=serializer.validated_data
            )
            response_serializer = ProductSerializer(product, context={'request': request})
            return Response({
                "success": True,
                "message": "Product added to marketplace successfully.",
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
        except Vendor.DoesNotExist:
            return Response({"error": "No vendor profile found for this user."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Update a product (Vendors only).
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = ProductCreateUpdateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            vendor = Vendor.objects.get(owner=request.user)
            product = MarketplaceService.update_marketplace_product(
                product_id=instance.id,
                vendor=vendor,
                data=serializer.validated_data
            )
            response_serializer = ProductSerializer(product, context={'request': request})
            return Response({
                "success": True,
                "message": "Product updated successfully.",
                "data": response_serializer.data
            })
        except Vendor.DoesNotExist:
            return Response({"error": "No vendor profile found for this user."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a product (Only the owner vendor).
        """
        instance = self.get_object()
        try:
            vendor = Vendor.objects.get(owner=request.user)
            MarketplaceService.delete_marketplace_product(
                product_id=instance.id,
                vendor=vendor
            )
            return Response({
                "success": True, 
                "message": "Product removed from marketplace."
            }, status=status.HTTP_200_OK)
        except Vendor.DoesNotExist:
            return Response({"error": "No vendor profile found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='catalog')
    def catalog(self, request):
        """
        Optimized catalog view with advanced filtering.
        """
        category = request.query_params.get('category')
        vendor = request.query_params.get('vendor')
        search = request.query_params.get('search')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        is_featured = request.query_params.get('is_featured')
        
        products = MarketplaceService.get_marketplace_catalog(
            category_slug=category,
            vendor_id=vendor,
            search=search,
            min_price=float(min_price) if min_price else None,
            max_price=float(max_price) if max_price else None,
            is_featured=is_featured.lower() == 'true' if is_featured else None
        )
        
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(products, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        })

    @action(detail=False, methods=['get'], url_path='featured')
    def featured(self, request):
        """
        Retrieve featured products.
        """
        limit = int(request.query_params.get('limit', 10))
        products = MarketplaceService.get_featured_products(limit=limit)
        serializer = self.get_serializer(products, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        })
