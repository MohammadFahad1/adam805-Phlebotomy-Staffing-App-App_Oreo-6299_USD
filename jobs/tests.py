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


class JobListingTests(APITestCase):
    def setUp(self):
        # Create client user
        self.client_user = User.objects.create_user(
            email="client_list@example.com",
            password="SecurePassword123!",
            full_name="Metro General Hospital Manager",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )
        # Create client profile
        self.client_profile = Client.objects.create(
            client=self.client_user,
            business_name="Metro General Hospital",
            business_type="healthcare",
            business_address_street="789 Broadway",
            business_address_city="New York",
            business_address_state="NY",
            business_address_zip="10003",
            contact_person_name="Jane Manager",
            business_phone="2125550200",
            business_license_number="BL-112233",
            business_description="General hospital",
            hourly_pay_rate="40.00",
            preferred_job_type="in_clinic_phlebotomy",
            work_preference="full_time",
            no_of_employees=50,
            is_approved=True
        )
        
        # Create different jobs for testing filters
        self.job_open = Job.objects.create(
            client=self.client_user,
            title="Blood Draw Service",
            professional_type="CP",
            description="Routine blood draw",
            location="789 Broadway, NY",
            city="New York",
            shift_date=datetime.date(2025, 8, 15),
            shift_start=datetime.time(23, 0),
            shift_end=datetime.time(7, 0),
            shift_duration=3,
            pay_type="hourly",
            pay_rate=30.00,
            job_type="full_day",
            status="open"
        )
        
        self.job_assigned = Job.objects.create(
            client=self.client_user,
            title="Pediatric Draw Support",
            professional_type="CP",
            description="Pediatric blood draw",
            location="789 Broadway, NY",
            city="New York",
            shift_date=datetime.date(2025, 8, 16),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(17, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=35.00,
            job_type="urgent",
            status="in_progress"
        )

        self.job_completed = Job.objects.create(
            client=self.client_user,
            title="Geriatric Venipuncture",
            professional_type="RN",
            description="Elderly clinic support",
            location="789 Broadway, NY",
            city="New York",
            shift_date=datetime.date(2025, 8, 17),
            shift_start=datetime.time(8, 0),
            shift_end=datetime.time(16, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=45.00,
            job_type="part_time",
            status="completed"
        )

        self.list_url = reverse('client-job-list')

    def test_client_job_list_all(self):
        self.client.force_authenticate(user=self.client_user)
        
        response = self.client.get(self.list_url, {"filter": "all"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check structure
        self.assertIn("success", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 3)
        
        # Check serialization fields of first item (most recent first, which is job_completed)
        job_data = response.data["results"][0]
        self.assertEqual(job_data["title"], "Geriatric Venipuncture")
        self.assertEqual(job_data["business_name"], "Metro General Hospital")
        self.assertEqual(job_data["distance"], "2.3 miles away")
        self.assertEqual(job_data["shift_duration"], "8 hours")
        self.assertEqual(job_data["shift_date"], "Aug 17, 2025")
        self.assertEqual(job_data["pay_rate"], "$45.00/hr")
        self.assertEqual(job_data["action_status"], "Completed")

    def test_client_job_list_new_job_filter(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.list_url, {"filter": "new_job"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Blood Draw Service")
        self.assertEqual(response.data["results"][0]["action_status"], "Invite")

    def test_client_job_list_assigned_filter(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.list_url, {"filter": "assigned"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Pediatric Draw Support")
        self.assertEqual(response.data["results"][0]["action_status"], "Assigned")

    def test_client_job_list_search(self):
        self.client.force_authenticate(user=self.client_user)
        
        # Search match
        response = self.client.get(self.list_url, {"search": "Pediatric"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Pediatric Draw Support")
        
        # Search no match
        response = self.client.get(self.list_url, {"search": "Nonexistent"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)


class JobTemplateListingTests(APITestCase):
    def setUp(self):
        # Create client user
        self.client_user = User.objects.create_user(
            email="client_template@example.com",
            password="SecurePassword123!",
            full_name="Template Manager",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )
        # Create client profile
        self.client_profile = Client.objects.create(
            client=self.client_user,
            business_name="Metro General Hospital",
            business_type="healthcare",
            business_address_street="789 Broadway",
            business_address_city="New York",
            business_address_state="NY",
            business_address_zip="10003",
            contact_person_name="Jane Manager",
            business_phone="2125550200",
            business_license_number="BL-112233",
            business_description="General hospital",
            hourly_pay_rate="40.00",
            preferred_job_type="in_clinic_phlebotomy",
            work_preference="full_time",
            no_of_employees=50,
            is_approved=True
        )
        
        # Create template imports
        from jobs.models import JobTemplate
        self.template = JobTemplate.objects.create(
            title="Regular Wednesday RN Shift",
            description="Emergency Department",
            location="789 Broadway, NY",
            city="New York",
            shift_duration=12,
            shift_date=datetime.date(2026, 9, 10),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(21, 0),
            pay_type="hourly",
            pay_rate=45.00,
            professional_type="RN",
            job_type="full_day"
        )
        
        self.templates_url = reverse('client-job-templates')

    def test_client_job_templates_success(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.templates_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertIn("success", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        
        tmpl = response.data["results"][0]
        self.assertEqual(tmpl["title"], "Regular Wednesday RN Shift")
        self.assertEqual(tmpl["professional_type"], "RN")
        self.assertEqual(tmpl["shift_duration"], "12-hour shift")
        self.assertEqual(tmpl["description"], "Emergency Department")
        self.assertIn("Last used", tmpl["last_used"])
        self.assertEqual(tmpl["pay_rate"], "$45.00/hr")

    def test_client_job_templates_search(self):
        self.client.force_authenticate(user=self.client_user)
        
        # Search match
        response = self.client.get(self.templates_url, {"search": "RN Shift"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        
        # Search no match
        response = self.client.get(self.templates_url, {"search": "Pediatric"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)


class PhlebotomistJobApplyViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job, JobAssignment, JobApplication
        from authentication.models import Phlebotomist
        import datetime

        # Create Client user
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="SecurePassword123!",
            full_name="Client User",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )

        # Create Phlebotomist users
        self.phleb_user1 = User.objects.create_user(
            email="phleb1@example.com",
            password="SecurePassword123!",
            full_name="Phleb One",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile1 = Phlebotomist.objects.create(
            user=self.phleb_user1,
            license_number="LIC-123456",
            license_expiry_date=datetime.date(2028, 12, 31),
            years_of_experience=5,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        self.phleb_user2 = User.objects.create_user(
            email="phleb2@example.com",
            password="SecurePassword123!",
            full_name="Phleb Two",
            phone_number="1234567892",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile2 = Phlebotomist.objects.create(
            user=self.phleb_user2,
            license_number="LIC-654321",
            license_expiry_date=datetime.date(2028, 12, 31),
            years_of_experience=3,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        # Create an open job to apply to
        self.open_job = Job.objects.create(
            client=self.client_user,
            title="Open Draw Job",
            description="Regular blood draw service.",
            location="123 Main Street",
            shift_date=datetime.date(2026, 9, 20),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(17, 0),
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.OPEN
        )

        # Create a draft job
        self.draft_job = Job.objects.create(
            client=self.client_user,
            title="Draft Job",
            description="Draft.",
            location="123 Main Street",
            shift_date=datetime.date(2026, 9, 20),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(17, 0),
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.DRAFT
        )

        self.apply_url = reverse('phlebotomist-job-apply', kwargs={'job_id': self.open_job.id})

    def test_apply_success(self):
        self.client.force_authenticate(user=self.phleb_user1)
        response = self.client.post(self.apply_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['detail'], "Job application submitted successfully.")

        from jobs.models import JobApplication
        self.assertTrue(JobApplication.objects.filter(job=self.open_job, phlebotomist=self.phleb_user1).exists())

    def test_apply_invalid_status(self):
        self.client.force_authenticate(user=self.phleb_user1)
        url = reverse('phlebotomist-job-apply', kwargs={'job_id': self.draft_job.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot apply", response.data['detail'])

    def test_apply_already_assigned(self):
        # Assign job to phleb2
        from jobs.models import JobAssignment
        JobAssignment.objects.create(
            job=self.open_job,
            phlebotomist=self.phleb_user2,
            client=self.client_user,
            status=JobAssignment.ACTIVE
        )

        self.client.force_authenticate(user=self.phleb_user1)
        response = self.client.post(self.apply_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "A phlebotomist is already assigned to this job.")

    def test_apply_schedule_conflict(self):
        # Create another job and assign to phleb1 on same date and overlapping hours
        import datetime
        from jobs.models import Job, JobAssignment
        conflict_job = Job.objects.create(
            client=self.client_user,
            title="Conflict Job",
            description="Overlap.",
            location="123 Main Street",
            shift_date=datetime.date(2026, 9, 20),
            shift_start=datetime.time(10, 0),
            shift_end=datetime.time(14, 0),
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.IN_PROGRESS
        )
        JobAssignment.objects.create(
            job=conflict_job,
            phlebotomist=self.phleb_user1,
            client=self.client_user,
            status=JobAssignment.ACTIVE
        )

        # Now phleb1 tries to apply to open_job (shift 9:00 - 17:00, which overlaps with 10:00 - 14:00)
        self.client.force_authenticate(user=self.phleb_user1)
        response = self.client.post(self.apply_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "You have a schedule conflict with another active job at this time.")

    def test_apply_duplicate(self):
        self.client.force_authenticate(user=self.phleb_user1)
        response = self.client.post(self.apply_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Apply again
        response = self.client.post(self.apply_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "You have already applied to this job.")



