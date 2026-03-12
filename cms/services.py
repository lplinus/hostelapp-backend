from .models import TermsAndConditions, PrivacyPolicy


class TermsService:

    @staticmethod
    def get_terms():
        return TermsAndConditions.objects.order_by("-effective_date").first()


class PrivacyPolicyService:

    @staticmethod
    def get_privacy_policy():
        return PrivacyPolicy.objects.order_by("-effective_date").first()