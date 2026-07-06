from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from authentication.models import Phlebotomist, PhlebotomistAvailability, Phlebotomist_skill, Phlebotomist_document
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
            "documents[0]document_name": "License Document",
            "documents[0]document_file": doc_file
        }
        
        response = self.client.post(self.register_url, data=payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data.get("message"),
            "That registration was sucessful and admin will review his profile and documents and once approve he/she can login!"
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
            "documents[0]document_name": "License Document",
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
            "documents[0]document_name": "Certification Resume",
            "documents[0]document_file": doc_file
        }
        
        response = self.client.post(self.register_url, data=payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data.get("message"),
            "That registration was sucessful and admin will review his profile and documents and once approve he/she can login!"
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
        self.assertEqual(doc.document_name, "Certification Resume")
        self.assertTrue(doc.document_file.name.startswith("phlebotomist_documents/resume"))
