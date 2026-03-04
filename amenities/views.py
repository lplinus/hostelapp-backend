from rest_framework import viewsets, permissions
from .models import Amenity
from .serializers import AmenitySerializer


class AmenityViewSet(viewsets.ModelViewSet):
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer
    permission_classes = [permissions.AllowAny]
