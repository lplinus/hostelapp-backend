from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PropertyDateBlockViewSet,
    HousekeepingTaskViewSet,
    DigitalGuestAccessViewSet,
    SecurityDepositLedgerViewSet,
    LiveMealPlanViewSet,
    LiveSeasonalMultiplierViewSet,
    LiveMinStayRuleViewSet,
    LivePromoCouponViewSet,
    LiveOperationsCalendarView,
    LiveOperationsAnalyticsView,
    LiveDynamicPriceView,
)

router = DefaultRouter()
router.register(r"date-blocks", PropertyDateBlockViewSet, basename="date-blocks")
router.register(r"housekeeping", HousekeepingTaskViewSet, basename="housekeeping")
router.register(r"guest-access", DigitalGuestAccessViewSet, basename="guest-access")
router.register(r"security-deposits", SecurityDepositLedgerViewSet, basename="security-deposits")
router.register(r"meal-plans", LiveMealPlanViewSet, basename="meal-plans")
router.register(r"seasonal-multipliers", LiveSeasonalMultiplierViewSet, basename="seasonal-multipliers")
router.register(r"min-stay-rules", LiveMinStayRuleViewSet, basename="min-stay-rules")
router.register(r"promo-coupons", LivePromoCouponViewSet, basename="promo-coupons")

urlpatterns = [
    path("calendar/", LiveOperationsCalendarView.as_view(), name="live-operations-calendar"),
    path("analytics/", LiveOperationsAnalyticsView.as_view(), name="live-operations-analytics"),
    path("dynamic-prices/", LiveDynamicPriceView.as_view(), name="live-operations-dynamic-prices"),
    path("", include(router.urls)),
]
