from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from .models import GuestProfile, GuestDocument, GuestDocumentSetting

User = get_user_model()


class GuestDocumentUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="guestuser1",
            email="guest1@example.com",
            password="TestPassword123!",
            role="guest"
        )
        self.client.force_authenticate(user=self.user)
        self.profile = GuestProfile.objects.get(user=self.user)
        self.profile.full_name = "Guest User One"
        self.profile.max_document_uploads = 6
        self.profile.save()

        # Other user for access control testing
        self.other_user = User.objects.create_user(
            username="otheruser2",
            email="other2@example.com",
            password="TestPassword123!",
            role="guest"
        )

    @patch("Hbackend.bunny_storage.BunnyCDNStorage._save", return_value="guest_documents/mocked_path.pdf")
    @patch("Hbackend.bunny_storage.BunnyCDNStorage.delete", return_value=True)
    def test_original_filename_preserved_and_category_separate(self, mock_delete, mock_save):
        """
        Scenario 1: Upload a document and verify original filename and extension are preserved
        and NOT replaced by 'Aadhaar'. Document category is maintained as separate metadata.
        """
        pdf_file = SimpleUploadedFile("rohit_passport_2026.pdf", b"%PDF-1.4 test document content", content_type="application/pdf")
        
        response = self.client.post("/api/guestprofile/documents/", {
            "file": pdf_file,
            "is_primary_guest": "true",
            "member_name": "Guest User One",
            "document_type": "passport",
            "document_number": "P12345678",
        }, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["file_name"], "rohit_passport_2026.pdf")
        self.assertEqual(response.data["document_type"], "passport")
        self.assertEqual(response.data["document_type_name"], "Passport")
        self.assertTrue(response.data["is_primary_guest"])

        # Fetch documents list and verify preservation on retrieval
        list_res = self.client.get("/api/guestprofile/documents/")
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        docs = list_res.data["documents"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["file_name"], "rohit_passport_2026.pdf")
        self.assertEqual(docs[0]["document_type"], "passport")

    @patch("Hbackend.bunny_storage.BunnyCDNStorage._save", return_value="guest_documents/mocked_path.jpg")
    @patch("Hbackend.bunny_storage.BunnyCDNStorage.delete", return_value=True)
    def test_primary_and_member_documents_upload(self, mock_delete, mock_save):
        """
        Scenario 2 & 3: Primary guest document + additional friend/member documents.
        """
        # Primary doc
        f1 = SimpleUploadedFile("my_id_card.jpg", b"fake image bytes", content_type="image/jpeg")
        r1 = self.client.post("/api/guestprofile/documents/", {
            "file": f1,
            "is_primary_guest": "true",
            "member_name": "Guest User One",
            "document_type": "aadhaar",
        }, format="multipart")
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)

        # Member doc 1 (Friend / Member)
        f2 = SimpleUploadedFile("ananya_driving_license.png", b"fake image bytes", content_type="image/png")
        r2 = self.client.post("/api/guestprofile/documents/", {
            "file": f2,
            "is_primary_guest": "false",
            "member_name": "Ananya Sharma",
            "document_type": "driving_license",
        }, format="multipart")
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.data["member_name"], "Ananya Sharma")
        self.assertEqual(r2.data["file_name"], "ananya_driving_license.png")
        self.assertFalse(r2.data["is_primary_guest"])

        # Check list response slots
        list_res = self.client.get("/api/guestprofile/documents/")
        self.assertEqual(list_res.data["uploaded_count"], 2)
        self.assertEqual(list_res.data["remaining_slots"], 4)

    @patch("Hbackend.bunny_storage.BunnyCDNStorage._save", return_value="guest_documents/mocked_path.pdf")
    @patch("Hbackend.bunny_storage.BunnyCDNStorage.delete", return_value=True)
    def test_document_limit_enforcement_max_6(self, mock_delete, mock_save):
        """
        Scenario 4: When max_document_uploads = 6, uploading a 7th document is rejected with 400.
        """
        self.profile.max_document_uploads = 6
        self.profile.save()

        # Upload 6 documents
        for i in range(6):
            f = SimpleUploadedFile(f"member_doc_{i+1}.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
            r = self.client.post("/api/guestprofile/documents/", {
                "file": f,
                "is_primary_guest": "true" if i == 0 else "false",
                "member_name": f"Member {i+1}",
                "document_type": "passport",
            }, format="multipart")
            self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

        # 7th document must fail
        f7 = SimpleUploadedFile("member_doc_7.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r7 = self.client.post("/api/guestprofile/documents/", {
            "file": f7,
            "is_primary_guest": "false",
            "member_name": "Member 7",
            "document_type": "passport",
        }, format="multipart")

        self.assertEqual(r7.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Upload limit reached", r7.data["detail"])

    @patch("Hbackend.bunny_storage.BunnyCDNStorage._save", return_value="guest_documents/mocked_path.pdf")
    @patch("Hbackend.bunny_storage.BunnyCDNStorage.delete", return_value=True)
    def test_document_limit_enforcement_max_7(self, mock_delete, mock_save):
        """
        Scenario 5: When max_document_uploads = 7, up to 7 documents are allowed, 8th is rejected.
        """
        self.profile.max_document_uploads = 7
        self.profile.save()

        for i in range(7):
            f = SimpleUploadedFile(f"doc_{i+1}.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
            r = self.client.post("/api/guestprofile/documents/", {
                "file": f,
                "is_primary_guest": "true" if i == 0 else "false",
                "member_name": f"Member {i+1}",
                "document_type": "aadhaar",
            }, format="multipart")
            self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

        # 8th document must fail
        f8 = SimpleUploadedFile("doc_8.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r8 = self.client.post("/api/guestprofile/documents/", {
            "file": f8,
            "is_primary_guest": "false",
            "member_name": "Member 8",
            "document_type": "aadhaar",
        }, format="multipart")

        self.assertEqual(r8.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Upload limit reached", r8.data["detail"])

    @patch("Hbackend.bunny_storage.BunnyCDNStorage._save", return_value="guest_documents/mocked_path.pdf")
    @patch("Hbackend.bunny_storage.BunnyCDNStorage.delete", return_value=True)
    def test_document_deletion_and_bunny_cleanup(self, mock_delete, mock_save):
        """
        Scenario 6: Document deletion removes record and triggers Bunny Storage deletion.
        """
        f = SimpleUploadedFile("delete_me.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r = self.client.post("/api/guestprofile/documents/", {
            "file": f,
            "is_primary_guest": "false",
            "member_name": "Friend to remove",
            "document_type": "voter_id",
        }, format="multipart")
        doc_id = r.data["id"]

        del_res = self.client.delete(f"/api/guestprofile/documents/{doc_id}/")
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)

        # Verify Bunny delete called
        self.assertTrue(mock_delete.called)

        # Verify document not returned in list
        list_res = self.client.get("/api/guestprofile/documents/")
        ids = [d["id"] for d in list_res.data["documents"]]
        self.assertNotIn(doc_id, ids)

    @patch("Hbackend.bunny_storage.BunnyCDNStorage._save", return_value="guest_documents/mocked_path.pdf")
    @patch("Hbackend.bunny_storage.BunnyCDNStorage.delete", return_value=True)
    def test_cross_user_access_control(self, mock_delete, mock_save):
        """
        Scenario 7: Guest A cannot access or delete Guest B's uploaded documents.
        """
        f = SimpleUploadedFile("secret_guest1_passport.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r = self.client.post("/api/guestprofile/documents/", {
            "file": f,
            "is_primary_guest": "true",
            "member_name": "Guest 1",
            "document_type": "passport",
        }, format="multipart")
        doc_id = r.data["id"]

        # Switch authentication to other_user
        self.client.force_authenticate(user=self.other_user)

        # Other user trying to delete doc_id must get 404
        bad_del = self.client.delete(f"/api/guestprofile/documents/{doc_id}/")
        self.assertEqual(bad_del.status_code, status.HTTP_404_NOT_FOUND)

        # Other user's document list must not contain doc_id
        other_list = self.client.get("/api/guestprofile/documents/")
        other_ids = [d["id"] for d in other_list.data["documents"]]
        self.assertNotIn(doc_id, other_ids)

    @patch("Hbackend.bunny_storage.BunnyCDNStorage._save", return_value="guest_documents/mocked_path.pdf")
    @patch("Hbackend.bunny_storage.BunnyCDNStorage.delete", return_value=True)
    def test_superadmin_settings_limit_override_to_3(self, mock_delete, mock_save):
        """
        Scenario 8: When superadmin sets MAX_GUEST_DOCUMENT_UPLOADS = 3 in settings,
        the profile API returns max_document_uploads = 3, documents API returns max_allowed = 3,
        up to 3 documents (including primary guest) can be uploaded, and a 4th document is rejected.
        """
        # Ensure profile has no custom override (defaults to admin setting)
        self.profile.max_document_uploads = None
        self.profile.save()

        # Superadmin sets limit to 3 in Django Admin
        GuestDocumentSetting.objects.update_or_create(pk=1, defaults={"max_document_uploads": 3})

        # 1. Profile API reflects 3
        profile_res = self.client.get("/api/guestprofile/me/")
        self.assertEqual(profile_res.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_res.data["max_document_uploads"], 3)

        # 2. Documents API reflects max_allowed = 3
        docs_res = self.client.get("/api/guestprofile/documents/")
        self.assertEqual(docs_res.status_code, status.HTTP_200_OK)
        self.assertEqual(docs_res.data["max_allowed"], 3)
        self.assertEqual(docs_res.data["remaining_slots"], 3)

        # 3. Upload Primary Guest document (Slot 1 of 3)
        f1 = SimpleUploadedFile("primary_aadhaar.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r1 = self.client.post("/api/guestprofile/documents/", {
            "file": f1,
            "is_primary_guest": "true",
            "member_name": "Guest User One",
            "document_type": "aadhaar",
        }, format="multipart")
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)

        # 4. Upload Companion Member 1 (Slot 2 of 3)
        f2 = SimpleUploadedFile("member_1_passport.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r2 = self.client.post("/api/guestprofile/documents/", {
            "file": f2,
            "is_primary_guest": "false",
            "member_name": "Companion One",
            "document_type": "passport",
        }, format="multipart")
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

        # 5. Upload Companion Member 2 (Slot 3 of 3)
        f3 = SimpleUploadedFile("member_2_dl.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r3 = self.client.post("/api/guestprofile/documents/", {
            "file": f3,
            "is_primary_guest": "false",
            "member_name": "Companion Two",
            "document_type": "driving_license",
        }, format="multipart")
        self.assertEqual(r3.status_code, status.HTTP_201_CREATED)

        # 6. Verify 3 of 3 slots used, 0 remaining
        check_res = self.client.get("/api/guestprofile/documents/")
        self.assertEqual(check_res.data["uploaded_count"], 3)
        self.assertEqual(check_res.data["remaining_slots"], 0)
        self.assertEqual(check_res.data["max_allowed"], 3)

        # 7. Uploading a 4th document MUST be rejected with HTTP 400
        f4 = SimpleUploadedFile("member_3_excess.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        r4 = self.client.post("/api/guestprofile/documents/", {
            "file": f4,
            "is_primary_guest": "false",
            "member_name": "Excess Member",
            "document_type": "voter_id",
        }, format="multipart")
        self.assertEqual(r4.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Upload limit reached", r4.data["detail"])
        self.assertIn("maximum of 3 documents", r4.data["detail"])

