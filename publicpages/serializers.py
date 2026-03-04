from rest_framework import serializers
from .models import (
    HomePage, WhyUsItem,Contact, ContactInfo, ContactFAQ, ContactMessage,Pricing, PricingPlan, PricingFeature, PricingFAQ
    )



class WhyUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhyUsItem
        fields = "__all__"


class HomePageSerializer(serializers.ModelSerializer):
    why_items = WhyUsSerializer(many=True, read_only=True)

    class Meta:
        model = HomePage
        fields = "__all__"


#About us serilazers======================================================
from rest_framework import serializers
from .models import About, AboutStat, AboutValue, AboutTeamMember


class AboutStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutStat
        fields = ["label", "value"]


class AboutValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutValue
        fields = ["icon_name", "title", "description"]


class AboutTeamMemberSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(read_only=True)

    class Meta:
        model = AboutTeamMember
        fields = ["name", "role", "photo"]


class AboutSerializer(serializers.ModelSerializer):
    stats = AboutStatSerializer(many=True, read_only=True)
    values = AboutValueSerializer(many=True, read_only=True)
    team_members = AboutTeamMemberSerializer(many=True, read_only=True)

    class Meta:
        model = About
        fields = [
            "hero_title",
            "hero_subtitle",
            "mission_title",
            "mission_description",
            "mission_card_title",
            "mission_card_description",
            "cta_title",
            "cta_button_text",
            "cta_button_url",
            "stats",
            "values",
            "team_members",
        ]

#Contat us serliazers





class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        fields = ["icon_name", "title", "value"]


class ContactFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactFAQ
        fields = ["question", "answer"]


class ContactSerializer(serializers.ModelSerializer):
    info_items = ContactInfoSerializer(many=True, read_only=True)
    faqs = ContactFAQSerializer(many=True, read_only=True)

    class Meta:
        model = Contact
        fields = [
            "hero_title",
            "hero_subtitle",
            "cta_title",
            "cta_button_text",
            "cta_button_url",
            "info_items",
            "faqs",
        ]

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]

    def create(self, validated_data):
        return ContactMessage.objects.create(**validated_data)



# Pricing Plan

class PricingFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingFeature
        fields = ["feature_text"]


class PricingPlanSerializer(serializers.ModelSerializer):
    features = PricingFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = PricingPlan
        fields = [
            "name",
            "description",
            "price",
            "currency_symbol",
            "period",
            "is_highlighted",
            "features",
        ]


class PricingFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingFAQ
        fields = ["question", "answer"]


class PricingSerializer(serializers.ModelSerializer):
    plans = PricingPlanSerializer(many=True, read_only=True)
    faqs = PricingFAQSerializer(many=True, read_only=True)

    class Meta:
        model = Pricing
        fields = [
            "hero_title",
            "hero_subtitle",
            "comparison_title",
            "comparison_description",
            "cta_title",
            "cta_button_text",
            "cta_button_url",
            "plans",
            "faqs",
        ]