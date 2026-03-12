from rest_framework import serializers
from .models import TermsAndConditions, PrivacyPolicy


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