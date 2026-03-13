from rest_framework import serializers
from .models import TermsAndConditions, PrivacyPolicy,FAQCategory,FAQ


class TermsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditions
        fields = [
            "title",
            "content",
            "effective_date",
            "email",
            "phone",
        ]

class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = [
            "title",
            "content",
            "effective_date",
            "email",
            "phone",
        ]

class FAQCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "order",
            "is_active",
        ]

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            "id",
            "category",
            "question",
            "answer",
            "slug",
            "order",
            "is_active",
            "view_count",
        ]
        read_only_fields = ("view_count",)