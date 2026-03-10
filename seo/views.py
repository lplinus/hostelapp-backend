from rest_framework import viewsets, permissions
from .models import SeoMeta
from .serializers import SeoMetaSerializer


class SeoMetaViewSet(viewsets.ModelViewSet):
    queryset = SeoMeta.objects.all()
    serializer_class = SeoMetaSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]
