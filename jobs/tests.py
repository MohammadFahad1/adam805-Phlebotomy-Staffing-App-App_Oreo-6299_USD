from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from authentication.models import Client
from jobs.models import Job
import datetime

User = get_user_model()

class JobPostingTests(APITestCase):
    def setUp(self):
        # Create a client user
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="SecurePassword123!",
            full_name="Smith Healthcare",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )
        # Create client profile
        self.client_profile = Client.objects.create(
            client=self.client_user,
            business_name="Smith Healthcare LLC",
            business_type="healthcare",
            business_address_street="123 Main St",
            business_address_city="New York",
            business_address_state="NY",
            business_address_zip="10001",
            contact_person_name="John Smith",
            business_phone="2125550100",
            business_license_number="BL-987654",
            business_description="Healthcare clinic",
            hourly_pay_rate="30.00",
            preferred_job_type="in_clinic_phlebotomy",
            work_preference="full_time",
            no_of_employees=10,
            is_approved=True
        )
        self.post_url = reverse('job-create')  # Check jobs/urls.py for name or use direct path

    def test_job_posting_success_and_sequential_ids(self):
        self.client.force_authenticate(user=self.client_user)
        
        payload1 = {
            "title": "Phlebotomist Needed for Blood Drive",
            "professional_type": "CP",
            "description": "Routine blood draw duty for a community drive.",
            "location": "123 Main Street, Suite 4",
            "city": "New York",
            "shift_date": "2026-09-01",
            "shift_start": "09:00",
            "shift_end": "17:00",
            "pay_type": "hourly",
            "pay_rate": "35.00",
            "job_type": "full_day"
        }
        
        response1 = self.client.post(self.post_url, data=payload1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertIn("job_id", response1.data)
        job_id1 = response1.data["job_id"]
        
        # Suffix year is last two digits of current year
        current_year_suffix = str(datetime.date.today().year)[-2:]
        self.assertTrue(job_id1.startswith(f"JB-{current_year_suffix}-"))
        self.assertEqual(job_id1[-6:], "000001")
        
        # Post a second job to test sequential generation
        payload2 = payload1.copy()
        payload2["title"] = "Second Phlebotomist Needed"
        response2 = self.client.post(self.post_url, data=payload2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        job_id2 = response2.data["job_id"]
        self.assertEqual(job_id2[-6:], "000002")

    def test_job_posting_invalid_times(self):
        self.client.force_authenticate(user=self.client_user)
        
        payload = {
            "title": "Invalid Shift Times Job",
            "professional_type": "CP",
            "description": "Job with invalid shift times.",
            "location": "123 Main Street",
            "shift_date": "2026-09-01",
            "shift_start": "17:00",
            "shift_end": "09:00",  # End is before start
            "pay_type": "hourly",
            "pay_rate": "35.00",
            "job_type": "full_day"
        }
        
        response = self.client.post(self.post_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("shift_end", response.data)
