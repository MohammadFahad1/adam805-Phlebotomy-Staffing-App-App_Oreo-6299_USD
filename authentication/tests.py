from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from authentication.models import Phlebotomist, PhlebotomistAvailability, Phlebotomist_skill, Phlebotomist_document
from authentication.models import Client, ClientWeeklySchedule, ClientDocument
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class PhlebotomistRegistrationTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('phlebotomist-register')

    def test_phlebotomist_registration_success(self):
        doc_file = SimpleUploadedFile("resume.pdf", b"pdf content", content_type="application/pdf")
        
        payload = {
            "full_name": "Jane Doe",
            "email": "janedoe@example.com",
            "password": "SecurePassword123!",
            "phone_number": "1234567890",
            "gender": "female",
            "dob": "1994-08-20",
            "license_number": "PHL-88291",
            "license_expiry_date": "2029-05-10",
            "years_of_experience": 4,
            "specialty": "general_phlebotomy",
            "work_preference": "part_time",
            "service_area": "Los Angeles",
            "address": "456 Oak Ave, Los Angeles, CA",
            "availabilities[0]day": "Monday",
            "availabilities[0]date": "2026-07-13",
            "availabilities[0]start_time": "08:00:00",
            "availabilities[0]end_time": "16:00:00",
            "availabilities[0]is_available": True,
            "skills[0]": "Pediatric Draw",
            "skills[1]": "Venipuncture",
            "documents[0]document_name": "license",
            "documents[0]document_file": doc_file
        }
        
        response = self.client.post(self.register_url, data=payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data.get("message"),
            "Phlebotomist account registered successfully. Your profile is pending admin approval. You will receive an email notification once your account is approved. You'll be able to log in after that!"
        )
        
        # Check user creation
        self.assertTrue(User.objects.filter(email="janedoe@example.com").exists())
        user = User.objects.get(email="janedoe@example.com")
        self.assertEqual(user.full_name, "Jane Doe")
        self.assertEqual(user.role, User.PHLEBOTOMIST)
        
        # Check phlebotomist profile
        self.assertTrue(Phlebotomist.objects.filter(user=user).exists())
        profile = user.phlebotomist_profile
        self.assertEqual(profile.license_number, "PHL-88291")
        
        # Check availabilities
        self.assertEqual(profile.availabilities.count(), 1)
        availability = profile.availabilities.first()
        self.assertEqual(availability.day, "Monday")
        
        # Check skills
        self.assertEqual(profile.skills.count(), 2)
        skills = list(profile.skills.values_list('skill_name', flat=True))
        self.assertIn("Pediatric Draw", skills)
        self.assertIn("Venipuncture", skills)

    def test_duplicate_email_fails(self):
        User.objects.create_user(
            email="existing@example.com",
            password="SecurePassword123!",
            full_name="Existing User",
            phone_number="0000000000",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST
        )
        
        doc_file = SimpleUploadedFile("resume.pdf", b"pdf content", content_type="application/pdf")
        
        payload = {
            "full_name": "New User",
            "email": "existing@example.com",
            "password": "SecurePassword123!",
            "phone_number": "1234567890",
            "gender": "female",
            "dob": "1994-08-20",
            "license_number": "PHL-88291",
            "license_expiry_date": "2029-05-10",
            "years_of_experience": 4,
            "specialty": "general_phlebotomy",
            "work_preference": "part_time",
            "service_area": "Los Angeles",
            "availabilities[0]day": "Monday",
            "availabilities[0]date": "2026-07-13",
            "availabilities[0]start_time": "08:00:00",
            "availabilities[0]end_time": "16:00:00",
            "availabilities[0]is_available": True,
            "skills[0]": "Pediatric Draw",
            "documents[0]document_name": "license",
            "documents[0]document_file": doc_file
        }
        
        response = self.client.post(self.register_url, data=payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_phlebotomist_registration_multipart_success(self):
        doc_file = SimpleUploadedFile("resume.pdf", b"pdf content", content_type="application/pdf")
        
        payload = {
            "full_name": "Bob Smith",
            "email": "bobsmith@example.com",
            "password": "SecurePassword123!",
            "phone_number": "0987654321",
            "gender": "male",
            "dob": "1988-11-30",
            "license_number": "PHL-77182",
            "license_expiry_date": "2028-10-15",
            "years_of_experience": 8,
            "specialty": "iv_insertion_or_therapy",
            "work_preference": "full_time",
            "service_area": "Chicago",
            "address": "789 Pine Rd, Chicago, IL",
            "availabilities[0]day": "Tuesday",
            "availabilities[0]date": "2026-07-14",
            "availabilities[0]start_time": "09:00:00",
            "availabilities[0]end_time": "17:00:00",
            "availabilities[0]is_available": True,
            "skills[0]": "IV Therapy",
            "skills[1]": "Oncology Draw",
            "documents[0]document_name": "license",
            "documents[0]document_file": doc_file
        }
        
        response = self.client.post(self.register_url, data=payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data.get("message"),
            "Phlebotomist account registered successfully. Your profile is pending admin approval. You will receive an email notification once your account is approved. You'll be able to log in after that!"
        )
        
        user = User.objects.get(email="bobsmith@example.com")
        self.assertEqual(user.full_name, "Bob Smith")
        
        profile = user.phlebotomist_profile
        self.assertEqual(profile.license_number, "PHL-77182")
        self.assertEqual(profile.specialty, "iv_insertion_or_therapy")
        
        self.assertEqual(profile.availabilities.count(), 1)
        self.assertEqual(profile.availabilities.first().day, "Tuesday")
        
        self.assertEqual(profile.skills.count(), 2)
        skills = list(profile.skills.values_list('skill_name', flat=True))
        self.assertIn("IV Therapy", skills)
        
        self.assertEqual(profile.documents.count(), 1)
        doc = profile.documents.first()
        self.assertEqual(doc.document_name, "license")
        self.assertTrue(doc.document_file.name.startswith("phlebotomist_documents/resume"))


class ClientRegistrationTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('client-register')

    def test_client_registration_success(self):
        from PIL import Image
        from io import BytesIO
        
        doc_file = SimpleUploadedFile("business_license.pdf", b"pdf content", content_type="application/pdf")
        
        image_io = BytesIO()
        Image.new('RGB', (1, 1), 'white').save(image_io, 'PNG')
        image_io.seek(0)
        signature_file = SimpleUploadedFile("signature.png", image_io.read(), content_type="image/png")
        
        payload = {
            "full_name": "John Smith",
            "email": "johnsmith@example.com",
            "password": "SecurePassword123!",
            "phone_number": "9876543210",
            "gender": "male",
            "dob": "1985-06-15",
            "business_name": "Smith Healthcare LLC",
            "business_type": "healthcare",
            "business_address_street": "123 Main Street",
            "business_address_city": "New York",
            "business_address_state": "NY",
            "business_address_zip": "10001",
            "contact_person_name": "John Smith",
            "business_phone": "2125550100",
            "business_license_number": "BL-987654",
            "business_description": "A private healthcare clinic offering routine blood draws.",
            "hourly_pay_rate": "30.00",
            "preferred_job_type": "in_clinic_phlebotomy",
            "work_preference": "full_time",
            "no_of_employees": 10,
            "signature": signature_file,
            "availabilities[0]day": "Monday",
            "availabilities[0]date": "2026-07-13",
            "availabilities[0]start_time": "08:00:00",
            "availabilities[0]end_time": "16:00:00",
            "availabilities[0]is_available": True,
            "documents[0]document_name": "license",
            "documents[0]document_file": doc_file
        }
        
        response = self.client.post(self.register_url, data=payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data.get("message"),
            "Client account registered successfully. Your profile is pending admin approval. You will receive an email notification once your account is approved. You'll be able to log in after that!"
        )
        
        # Check user creation
        self.assertTrue(User.objects.filter(email="johnsmith@example.com").exists())
        user = User.objects.get(email="johnsmith@example.com")
        self.assertEqual(user.full_name, "John Smith")
        self.assertEqual(user.role, User.CLIENT)
        
        # Check client profile
        self.assertTrue(Client.objects.filter(client=user).exists())
        profile = user.client_profile
        self.assertEqual(profile.business_name, "Smith Healthcare LLC")
        self.assertTrue(profile.signature.name.startswith("client_signatures/signature"))
        
        # Check weekly schedule (availabilities)
        self.assertEqual(profile.availabilities.count(), 1)
        schedule = profile.availabilities.first()
        self.assertEqual(schedule.day, "Monday")
        
        self.assertEqual(profile.documents.count(), 1)
        doc = profile.documents.first()
        self.assertEqual(doc.document_name, "license")
        self.assertTrue(doc.document_file.name.startswith("client_documents/business_license"))


class PhlebotomistProfileUpdateTests(APITestCase):

    def setUp(self):
        self.update_url = reverse('phlebotomist-profile-update')
        self.phleb_user = User.objects.create_user(
            email="phleb@example.com",
            password="SecurePassword123!",
            full_name="John Doe",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST
        )
        self.phleb_profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number="PHL-123456",
            license_expiry_date="2027-12-31",
            years_of_experience=5,
            specialty="general_phlebotomy",
            work_preference="full_time",
            service_area="Brooklyn",
            address="123 Street"
        )
        # Create some skills and availabilities initially
        Phlebotomist_skill.objects.create(phlebotomist=self.phleb_profile, skill_name="Venipuncture")
        PhlebotomistAvailability.objects.create(
            phlebotomist=self.phleb_profile,
            day="Monday",
            date="2026-07-13",
            start_time="08:00:00",
            end_time="16:00:00",
            is_available=True
        )

    def test_update_single_field_leaves_others_unchanged(self):
        self.client.force_authenticate(user=self.phleb_user)
        payload = {
            "full_name": "Updated John Doe"
        }
        response = self.client.patch(self.update_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.phleb_user.refresh_from_db()
        self.assertEqual(self.phleb_user.full_name, "Updated John Doe")
        # Ensure other fields are completely untouched
        self.assertEqual(self.phleb_user.phone_number, "1234567890")
        self.phleb_profile.refresh_from_db()
        self.assertEqual(self.phleb_profile.license_number, "PHL-123456")
        self.assertEqual(self.phleb_profile.skills.count(), 1)
        self.assertEqual(self.phleb_profile.availabilities.count(), 1)

    def test_update_optional_blank_ignored(self):
        self.client.force_authenticate(user=self.phleb_user)
        payload = {
            "phone_number": "9876543210",
            "license_number": "",
            "dob": "null",
            "years_of_experience": "undefined",
            "skills": "",
            "availabilities": None
        }
        response = self.client.patch(self.update_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.phleb_user.refresh_from_db()
        self.assertEqual(self.phleb_user.phone_number, "9876543210")
        self.assertEqual(str(self.phleb_user.dob), "1990-01-01") # stayed the same
        
        self.phleb_profile.refresh_from_db()
        self.assertEqual(self.phleb_profile.license_number, "PHL-123456") # stayed the same
        self.assertEqual(self.phleb_profile.years_of_experience, 5) # stayed the same
        self.assertEqual(self.phleb_profile.skills.count(), 1) # stayed the same
        self.assertEqual(self.phleb_profile.availabilities.count(), 1) # stayed the same

    def test_nullable_address_can_be_cleared(self):
        self.client.force_authenticate(user=self.phleb_user)
        payload = {
            "address": ""
        }
        response = self.client.patch(self.update_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.phleb_profile.refresh_from_db()
        self.assertIsNone(self.phleb_profile.address)


class ClientProfileUpdateTests(APITestCase):

    def setUp(self):
        self.update_url = reverse('client-profile-update')
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="SecurePassword123!",
            full_name="John Client",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.CLIENT
        )
        self.client_profile = Client.objects.create(
            client=self.client_user,
            business_name="Acme Health",
            business_type="healthcare",
            business_address_street="456 Elm St",
            business_address_city="Brooklyn",
            business_address_state="NY",
            business_address_zip="11201",
            contact_person_name="Jane Contact",
            business_phone="0987654321",
            business_license_number="BL-12345",
            business_description="Test Description",
            hourly_pay_rate=30.00,
            preferred_job_type="in_clinic_phlebotomy",
            work_preference="full_time",
            no_of_employees=10
        )
        ClientWeeklySchedule.objects.create(
            client=self.client_profile,
            day="Monday",
            date="2026-07-13",
            start_time="08:00:00",
            end_time="16:00:00",
            is_available=True
        )

    def test_update_single_field_leaves_others_unchanged(self):
        self.client.force_authenticate(user=self.client_user)
        payload = {
            "business_name": "Updated Acme Health"
        }
        response = self.client.patch(self.update_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.client_profile.refresh_from_db()
        self.assertEqual(self.client_profile.business_name, "Updated Acme Health")
        self.assertEqual(self.client_profile.business_address_city, "Brooklyn")
        self.assertEqual(self.client_profile.availabilities.count(), 1)

    def test_update_optional_blank_ignored(self):
        self.client.force_authenticate(user=self.client_user)
        payload = {
            "business_address_city": "Manhattan",
            "business_name": "",
            "business_type": "null",
            "business_address_state": "undefined",
            "availabilities": None
        }
        response = self.client.patch(self.update_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.client_profile.refresh_from_db()
        self.assertEqual(self.client_profile.business_address_city, "Manhattan")
        self.assertEqual(self.client_profile.business_name, "Acme Health") # stayed the same
        self.assertEqual(self.client_profile.business_type, "healthcare") # stayed the same
        self.assertEqual(self.client_profile.business_address_state, "NY") # stayed the same
        self.assertEqual(self.client_profile.availabilities.count(), 1) # stayed the same


