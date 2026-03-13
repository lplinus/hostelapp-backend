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
    def get_faqs(search_query=None, category_id=None):
        from django.db.models import Q
        queryset = FAQ.objects.filter(is_active=True)
        
        # Robust category filtering
        if category_id:
            try:
                # Handle both string and int, ignore 0 or '0' for 'All'
                cat_id = int(category_id)
                if cat_id > 0:
                    queryset = queryset.filter(category__id=cat_id)
            except (ValueError, TypeError):
                pass
            
        # Robust search filtering
        if search_query and str(search_query).strip():
            query = str(search_query).strip()
            queryset = queryset.filter(
                Q(question__icontains=query) |
                Q(answer__icontains=query)
            )
            
        return queryset.order_by("order", "-created_at")

    @staticmethod
    def search_faqs(query):
        from django.db.models import Q
        queryset = FAQ.objects.filter(is_active=True)
        if query and str(query).strip():
            q = str(query).strip()
            queryset = queryset.filter(
                Q(question__icontains=q) | 
                Q(answer__icontains=q)
            )
        return queryset.order_by("order", "-created_at")

    @staticmethod
    def get_faq(slug):
        return FAQ.objects.filter(is_active=True, slug=slug).first()

    @staticmethod
    def increment_view_count(faq):
        faq.view_count += 1
        faq.save()
        return faq