from rest_framework import views, permissions, response
from vendors.models import Vendor
from vendors.serializers import VendorSerializer
from .models import Product
from .serializers import ProductSerializer
from django.db.models import Q

class MarketplaceSearchAPIView(views.APIView):
    """
    Separate API for marketplace searching to avoid modifying existing discovery endpoints.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('search', '')
        search_type = request.query_params.get('type', 'all') # 'vendors', 'products', or 'all'
        
        results = {}
        
        if not query:
            return response.Response({"vendors": [], "products": []})

        if search_type in ['vendors', 'all']:
            vendors = Vendor.objects.filter(
                Q(business_name__icontains=query) |
                Q(description__icontains=query) |
                Q(address__icontains=query) |
                Q(vendor_types__icontains=query)
            ).prefetch_related('marketplace_products')
            results['vendors'] = VendorSerializer(vendors, many=True, context={'request': request}).data

        if search_type in ['products', 'all']:
            products = Product.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query) |
                Q(vendor__business_name__icontains=query)
            ).select_related('vendor', 'category')
            results['products'] = ProductSerializer(products, many=True, context={'request': request}).data

        return response.Response({
            "success": True,
            "query": query,
            "data": results
        })
