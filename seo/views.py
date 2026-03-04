from rest_framework import viewsets, permissions
from .models import SeoMeta
from .serializers import SeoMetaSerializer


class SeoMetaViewSet(viewsets.ModelViewSet):
    queryset = SeoMeta.objects.all()
    serializer_class = SeoMetaSerializer
    permission_classes = [permissions.AllowAny]
