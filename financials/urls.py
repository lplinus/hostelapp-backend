from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FinancialTransactionViewSet,
    PayoutBatchViewSet,
    GstInvoiceViewSet,
    PropertyExpenseViewSet,
    FinancialsOverviewView,
)

router = DefaultRouter()
router.register(r"transactions", FinancialTransactionViewSet, basename="financial-transactions")
router.register(r"payouts", PayoutBatchViewSet, basename="financial-payouts")
router.register(r"invoices", GstInvoiceViewSet, basename="financial-invoices")
router.register(r"expenses", PropertyExpenseViewSet, basename="financial-expenses")

urlpatterns = [
    path("overview/", FinancialsOverviewView.as_view(), name="financials-overview"),
    path("", include(router.urls)),
]
