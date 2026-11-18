from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.user_views import UserViewSet
from .views.document_verification_views import (
    OwnerDocumentVerificationView,
    OwnerDocumentUploadView,
    OwnerDocumentDeleteView,
    SuperAdminVerificationListView,
    SuperAdminDocumentActionView,
)

app_name = "accounts"

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    # Document Verification Endpoints
    path("my-documents/", OwnerDocumentVerificationView.as_view(), name="my_documents"),
    path("my-documents/upload/", OwnerDocumentUploadView.as_view(), name="my_documents_upload"),
    path("my-documents/<int:document_id>/", OwnerDocumentDeleteView.as_view(), name="my_documents_delete"),
    path("superadmin/verifications/", SuperAdminVerificationListView.as_view(), name="superadmin_verifications"),
    path("superadmin/documents/<int:document_id>/action/", SuperAdminDocumentActionView.as_view(), name="superadmin_document_action"),

    path("", include(router.urls)),
]
