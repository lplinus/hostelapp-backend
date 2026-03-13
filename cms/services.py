from cms.models import TermsAndConditions, PrivacyPolicy, FAQCategory, FAQ


class TermsService:

    @staticmethod
    def get_terms():
        return TermsAndConditions.objects.order_by("-effective_date").first()


class PrivacyPolicyService:

    @staticmethod
    def get_privacy_policy():
        return PrivacyPolicy.objects.order_by("-effective_date").first()

class FAQCategoryService:

    @staticmethod
    def get_faq_categories():
        return FAQCategory.objects.filter(is_active=True).order_by("order", "name")

class FAQService:

    @staticmethod
    def get_faqs():
        return FAQ.objects.filter(is_active=True).order_by("order", "-created_at")

    @staticmethod
    def get_faq(slug):
        return FAQ.objects.filter(is_active=True, slug=slug).first()

    @staticmethod
    def increment_view_count(faq):
        faq.view_count += 1
        faq.save()
        return faq