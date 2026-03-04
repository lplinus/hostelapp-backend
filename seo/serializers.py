from rest_framework import serializers
from .models import SeoMeta


class SeoMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoMeta
        fields = "__all__"
