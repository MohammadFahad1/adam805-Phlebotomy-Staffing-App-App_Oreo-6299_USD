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


class PhlebotomistAvailableJobsAPIViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job, JobAssignment, JobApplication
        from authentication.models import Phlebotomist
        import datetime

        # Create Client user
        self.client_user = User.objects.create_user(
            email="client_avail@example.com",
            password="SecurePassword123!",
            full_name="Client Available",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )

        # Create Phlebotomist user
        self.phleb_user = User.objects.create_user(
            email="phleb_avail@example.com",
            password="SecurePassword123!",
            full_name="Phleb Avail",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number="LIC-888888",
            license_expiry_date=datetime.date(2028, 12, 31),
            years_of_experience=4,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        # 1. Job with status approved and no assignment (should be available)
        self.j1 = Job.objects.create(
            client=self.client_user,
            title="Blood draw Station",
            description="Regular blood draw service.",
            location="123 Main Street, New York",
            city="New York",
            shift_date=datetime.date(2026, 9, 20),
            shift_start=datetime.time(23, 0), # Night shift
            shift_end=datetime.time(7, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        # 2. Job with status open and pending assignment (should be available)
        self.j2 = Job.objects.create(
            client=self.client_user,
            title="ICU Nurse",
            description="ICU Nurse Shift.",
            location="456 Broadway, New York",
            city="New York",
            shift_date=datetime.date(2026, 9, 20),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(17, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.OPEN,
            job_type=Job.FULL_DAY
        )
        # Create PENDING assignment
        JobAssignment.objects.create(
            job=self.j2,
            phlebotomist=self.phleb_user,
            client=self.client_user,
            status=JobAssignment.PENDING
        )

        # 3. Job with active assignment (should NOT be available)
        self.j3 = Job.objects.create(
            client=self.client_user,
            title="Physical Therapist",
            description="Physical Therapist Needed.",
            location="789 Broadway",
            city="New York",
            shift_date=datetime.date(2026, 9, 20),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(17, 0),
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.OPEN,
            job_type=Job.URGENT
        )
        JobAssignment.objects.create(
            job=self.j3,
            phlebotomist=self.phleb_user,
            client=self.client_user,
            status=JobAssignment.ACTIVE
        )

        self.list_url = reverse('phlebotomist-available-jobs')

    def test_get_available_jobs_success(self):
        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Expect only j1 and j2 to be available (j3 has active assignment)
        results = response.data['results']
        self.assertEqual(len(results), 2)
        
        # Verify structure
        j1_res = next(x for x in results if x['id'] == self.j1.id)
        self.assertEqual(j1_res['title'], "Blood draw Station")
        self.assertEqual(j1_res['pay_rate'], "$30.00/hr")
        self.assertEqual(j1_res['distance'], "2.3 miles away")
        self.assertEqual(j1_res['shift_time'], "11:00 PM - 7:00 AM")
        self.assertEqual(j1_res['job_type'], "Urgent")
        self.assertEqual(j1_res['action_status'], "Apply")
        self.assertEqual(j1_res['applied'], False)

    def test_get_available_jobs_applied_status(self):
        # Create an application for j1 by self.phleb_user
        from jobs.models import JobApplication
        JobApplication.objects.create(
            job=self.j1,
            phlebotomist=self.phleb_user,
            status=JobApplication.PENDING
        )

        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        j1_res = next(x for x in results if x['id'] == self.j1.id)
        self.assertEqual(j1_res['applied'], True)
        self.assertEqual(j1_res['action_status'], "Applied")

    def test_filter_tabs(self):
        self.client.force_authenticate(user=self.phleb_user)

        # 1. Night shift filter (should return j1 only)
        response = self.client.get(self.list_url, {'filter': 'Night Shift'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.j1.id)

        # 2. Today filter (should return 0 because shift_date is 2026-09-20, not today)
        response = self.client.get(self.list_url, {'filter': 'today'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 0)

    def test_search_jobs(self):
        self.client.force_authenticate(user=self.phleb_user)

        # Search match for ICU
        response = self.client.get(self.list_url, {'search': 'ICU'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.j2.id)


class PhlebotomistAppliedJobsAPIViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job, JobApplication
        from authentication.models import Phlebotomist
        import datetime

        # Create Client user
        self.client_user = User.objects.create_user(
            email="client_applied@example.com",
            password="SecurePassword123!",
            full_name="Client Applied",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )

        # Create Phlebotomist user
        self.phleb_user = User.objects.create_user(
            email="phleb_applied@example.com",
            password="SecurePassword123!",
            full_name="Phleb Applied",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number="LIC-999999",
            license_expiry_date=datetime.date(2028, 12, 31),
            years_of_experience=4,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        # Create 2 jobs
        self.j1 = Job.objects.create(
            client=self.client_user,
            title="Blood draw Station",
            description="Regular blood draw service.",
            location="123 Main Street, New York",
            city="New York",
            shift_date=datetime.date(2026, 9, 20),
            shift_start=datetime.time(23, 0), # Night shift
            shift_end=datetime.time(7, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        self.j2 = Job.objects.create(
            client=self.client_user,
            title="Physical Therapist",
            description="Physical Therapist Needed.",
            location="789 Broadway",
            city="New York",
            shift_date=datetime.date(2026, 9, 20),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(17, 0),
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.OPEN,
            job_type=Job.URGENT
        )

        # Apply to j1 only
        JobApplication.objects.create(
            job=self.j1,
            phlebotomist=self.phleb_user,
            status=JobApplication.PENDING
        )

        self.applied_url = reverse('phlebotomist-applied-jobs')

    def test_get_applied_jobs_success(self):
        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.get(self.applied_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Expect only j1 to be returned since they only applied to j1
        results = response.data['results']
        self.assertEqual(len(results), 1)
        
        self.assertEqual(results[0]['id'], self.j1.id)
        self.assertEqual(results[0]['title'], "Blood draw Station")
        self.assertEqual(results[0]['applied'], True)
        self.assertEqual(results[0]['action_status'], "Applied")


class PhlebotomistJobDetailsAPIViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job
        from authentication.models import Phlebotomist, Client
        import datetime

        # Create Client user
        self.client_user = User.objects.create_user(
            email="client_details@example.com",
            password="SecurePassword123!",
            full_name="Dr. Ratul Hassan",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )
        self.client_profile = Client.objects.create(
            client=self.client_user,
            business_name="Community Health Center",
            business_type=Client.HEALTHCARE,
            business_address_street="123 ABC Street Mirpur",
            business_address_city="Dhaka",
            business_address_state="Dhaka Division",
            business_address_zip="1216",
            contact_person_name="Dr. Ratul Hassan",
            business_phone="(123) 123-4567",
            business_license_number="LIC-11111",
            business_description="Community clinic.",
            hourly_pay_rate=25.00,
            preferred_job_type=Client.MOBILE_BLOOD_DRAW,
            work_preference=Client.FULL_TIME
        )

        # Create Phlebotomist user
        self.phleb_user = User.objects.create_user(
            email="phleb_details@example.com",
            password="SecurePassword123!",
            full_name="Phleb Details",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number="LIC-777777",
            license_expiry_date=datetime.date(2028, 12, 31),
            years_of_experience=4,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        # Create Job
        self.job = Job.objects.create(
            client=self.client_user,
            title="Blood Draw Station",
            description="Perform venipuncture and capillary punctures.",
            location="123 ABC Street Mirpur, Dhaka 1216",
            city="Dhaka",
            shift_date=datetime.date(2025, 7, 15),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(13, 0),
            shift_duration=4,
            pay_type="hourly",
            pay_rate=25.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        self.detail_url = reverse('phlebotomist-job-detail', kwargs={'job_id': self.job.id})

    def test_get_job_details_success(self):
        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['title'], "Blood Draw Station")
        self.assertEqual(data['client_name'], "Dr. Ratul Hassan")
        self.assertEqual(data['client_address'], "123 ABC Street Mirpur, Dhaka, Dhaka Division 1216")
        self.assertEqual(data['client_business_name'], "(Community Health Center)")
        self.assertEqual(data['client_phone'], "(123) 123-4567")
        self.assertEqual(data['shift_date'], "July 15, 2025")
        self.assertEqual(data['shift_time'], "9:00 AM - 1:00 PM (4 hours)")
        self.assertEqual(data['formatted_job_id'], f"#{self.job.id}")
        self.assertEqual(data['hourly_rate'], "$25.00")
        self.assertEqual(data['total_hours'], "4.0 hrs")
        self.assertEqual(data['subtotal'], "$100.00")
        self.assertEqual(data['service_fee'], "-$5.00")
        self.assertEqual(data['tax_withholding'], "-$15.00")
        self.assertEqual(data['total_earnings'], "$80.00")
        self.assertEqual(data['applied'], False)
        self.assertEqual(data['application_status'], None)

    def test_get_job_details_applied(self):
        from jobs.models import JobApplication
        JobApplication.objects.create(
            job=self.job,
            phlebotomist=self.phleb_user,
            status=JobApplication.PENDING
        )

        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['applied'], True)
        self.assertEqual(data['application_status'], 'pending')


class PhlebotomistPendingJobListAPIViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job, JobAssignment
        from authentication.models import Phlebotomist
        import datetime

        # Create Client user
        self.client_user = User.objects.create_user(
            email="client_pending@example.com",
            password="SecurePassword123!",
            full_name="Client Pending",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )

        # Create Phlebotomist user
        self.phleb_user = User.objects.create_user(
            email="phleb_pending@example.com",
            password="SecurePassword123!",
            full_name="Phleb Pending",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number="LIC-888888",
            license_expiry_date=datetime.date(2028, 12, 31),
            years_of_experience=4,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        # Create 2 jobs
        self.j1 = Job.objects.create(
            client=self.client_user,
            title="Massage Therapist",
            description="Massage session.",
            location="123 Main St, Anytown, USA",
            city="Anytown",
            shift_date=datetime.date(2025, 8, 14),
            shift_start=datetime.time(10, 0),
            shift_end=datetime.time(18, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        self.j2 = Job.objects.create(
            client=self.client_user,
            title="Yoga Instructor",
            description="Yoga session.",
            location="456 Oak Ave, Otherville, USA",
            city="Otherville",
            shift_date=datetime.date(2025, 8, 15),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(17, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        # Create a pending assignment for j1
        self.assignment = JobAssignment.objects.create(
            job=self.j1,
            phlebotomist=self.phleb_user,
            client=self.client_user,
            status=JobAssignment.PENDING
        )

        self.pending_url = reverse('phlebotomist-pending-jobs')

    def test_get_pending_jobs_success(self):
        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.get(self.pending_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], "Pending jobs list retrieved successfully.")
        
        # Expect only j1 to be returned since it is assigned to this phlebotomist
        jobs = data['data']
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['id'], self.j1.id)
        self.assertEqual(jobs[0]['title'], "Massage Therapist")
        self.assertEqual(jobs[0]['applied'], False)
        self.assertEqual(jobs[0]['accepted'], False)


class PhlebotomistAcceptJobsAPIViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job, JobAssignment
        from authentication.models import Phlebotomist
        import datetime

        # Create Client user
        self.client_user = User.objects.create_user(
            email="client_accept@example.com",
            password="SecurePassword123!",
            full_name="Client Accept",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )

        # Create Phlebotomist user
        self.phleb_user = User.objects.create_user(
            email="phleb_accept@example.com",
            password="SecurePassword123!",
            full_name="Phleb Accept",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number="LIC-555555",
            license_expiry_date=datetime.date(2028, 12, 31),
            years_of_experience=4,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        # Create Job
        self.job = Job.objects.create(
            client=self.client_user,
            title="Blood draw Station",
            description="Regular blood draw service.",
            location="123 Main Street, New York",
            city="New York",
            shift_date=datetime.date(2026, 9, 20),
            shift_start=datetime.time(23, 0),
            shift_end=datetime.time(7, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        # Create a pending assignment
        self.assignment = JobAssignment.objects.create(
            job=self.job,
            phlebotomist=self.phleb_user,
            client=self.client_user,
            status=JobAssignment.PENDING
        )

        self.accept_url = reverse('phlebotomist-accept-job', kwargs={'job_id': self.job.id})

    def test_accept_job_success(self):
        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.patch(self.accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], "Job accepted successfully.")

        # Verify job and assignment status
        self.job.refresh_from_db()
        self.assignment.refresh_from_db()
        self.assertEqual(self.job.status, "in_progress")
        self.assertEqual(self.assignment.status, "active")
        self.assertTrue(self.assignment.signed_by_phlebotomist)


class PhlebotomistRejectJobsAPIViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job, JobAssignment
        from authentication.models import Phlebotomist
        import datetime

        self.client_user = User.objects.create_user(
            email="client_reject@example.com",
            password="SecurePassword123!",
            full_name="Client Reject",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )

        self.phleb_user = User.objects.create_user(
            email="phleb_reject@example.com",
            password="SecurePassword123!",
            full_name="Phleb Reject",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number="LIC-666666",
            license_expiry_date=datetime.date(2028, 12, 31),
            years_of_experience=4,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        self.job = Job.objects.create(
            client=self.client_user,
            title="Blood draw Station",
            description="Regular blood draw service.",
            location="123 Main Street, New York",
            city="New York",
            shift_date=datetime.date(2026, 9, 20),
            shift_start=datetime.time(23, 0),
            shift_end=datetime.time(7, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        self.assignment = JobAssignment.objects.create(
            job=self.job,
            phlebotomist=self.phleb_user,
            client=self.client_user,
            status=JobAssignment.PENDING
        )

        self.reject_url = reverse('phlebotomist-reject-job', kwargs={'job_id': self.job.id})

    def test_reject_job_success(self):
        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.patch(self.reject_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], "Job assignment rejected successfully.")

        # Verify job and assignment status
        from jobs.models import JobAssignment
        self.assertFalse(JobAssignment.objects.filter(id=self.assignment.id).exists())
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.APPROVED)


class UserRatingsReviewsAPIViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job
        from authentication.models import Phlebotomist, Client
        from communication.models import Review
        import datetime

        # Create Client user 1 (being reviewed)
        self.client_user = User.objects.create_user(
            email="client_rev@example.com",
            password="SecurePassword123!",
            full_name="Client Reviewed",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )
        self.client_profile = Client.objects.create(
            client=self.client_user,
            business_name="Community Health Center",
            business_type=Client.HEALTHCARE,
            business_address_street="123 ABC Street Mirpur",
            business_address_city="Dhaka",
            business_address_state="Dhaka Division",
            business_address_zip="1216",
            contact_person_name="Client Reviewed",
            business_phone="(123) 123-4567",
            business_license_number="LIC-11111",
            business_description="Community clinic.",
            hourly_pay_rate=25.00,
            preferred_job_type=Client.MOBILE_BLOOD_DRAW,
            work_preference=Client.FULL_TIME,
            is_approved=True
        )

        # Create Phlebotomist user 1 (being reviewed)
        self.phleb_user = User.objects.create_user(
            email="phleb_rev@example.com",
            password="SecurePassword123!",
            full_name="Phleb Reviewed",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number="LIC-777777",
            license_expiry_date=datetime.date(2028, 12, 31),
            years_of_experience=4,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        # Create Job
        self.job = Job.objects.create(
            client=self.client_user,
            title="Blood Draw Station",
            description="Perform venipuncture.",
            location="123 ABC Street Mirpur, Dhaka 1216",
            city="Dhaka",
            shift_date=datetime.date(2025, 7, 15),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(13, 0),
            shift_duration=4,
            pay_type="hourly",
            pay_rate=25.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        # Create Review 1 (Client reviews Phlebotomist)
        self.r1 = Review.objects.create(
            job=self.job,
            reviewer=self.client_user,
            reviewed=self.phleb_user,
            rating=5,
            comment="Excellent service!",
            status=Review.APPROVED
        )

        # Create Review 2 (Phlebotomist reviews Client)
        self.r2 = Review.objects.create(
            job=self.job,
            reviewer=self.phleb_user,
            reviewed=self.client_user,
            rating=4,
            comment="Very nice client, on time.",
            status=Review.APPROVED
        )

        self.phleb_reviews_url = reverse('phlebotomist-ratings-reviews')
        self.client_reviews_url = reverse('client-ratings-reviews')

    def test_phlebotomist_ratings_reviews_success(self):
        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.get(self.phleb_reviews_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['average_rating'], 5.0)
        self.assertEqual(data['data']['total_reviews_count'], 1)
        self.assertEqual(len(data['data']['reviews']), 1)
        self.assertEqual(data['data']['reviews'][0]['reviewer_name'], "Client Reviewed")
        self.assertEqual(data['data']['reviews'][0]['comment'], "Excellent service!")
        self.assertEqual(data['data']['reviews'][0]['rating'], 5)

    def test_client_ratings_reviews_success(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.client_reviews_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['average_rating'], 4.0)
        self.assertEqual(data['data']['total_reviews_count'], 1)
        self.assertEqual(len(data['data']['reviews']), 1)
        self.assertEqual(data['data']['reviews'][0]['reviewer_name'], "Phleb Reviewed")
        self.assertEqual(data['data']['reviews'][0]['comment'], "Very nice client, on time.")
        self.assertEqual(data['data']['reviews'][0]['rating'], 4)


class ReportUserAPIViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job
        from authentication.models import Phlebotomist, Client
        import datetime

        # Client user
        self.client_user = User.objects.create_user(
            email="client_rep@example.com",
            password="SecurePassword123!",
            full_name="Client Reporter",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )

        # Phlebotomist user
        self.phleb_user = User.objects.create_user(
            email="phleb_rep@example.com",
            password="SecurePassword123!",
            full_name="Phleb Reported",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number="LIC-888888",
            license_expiry_date=datetime.date(2028, 12, 31),
            years_of_experience=4,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        # Job
        self.job = Job.objects.create(
            client=self.client_user,
            title="Blood Draw Station",
            description="Perform venipuncture.",
            location="123 ABC Street Mirpur, Dhaka 1216",
            city="Dhaka",
            shift_date=datetime.date(2025, 7, 15),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(13, 0),
            shift_duration=4,
            pay_type="hourly",
            pay_rate=25.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        self.report_url = reverse('report-user')

    def test_get_report_user_details_success(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.report_url, {'user_id': self.phleb_user.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['full_name'], "Phleb Reported")
        self.assertEqual(data['data']['subtitle'], "General Phlebotomy • 4 years exp")

    def test_post_report_user_success_with_job(self):
        self.client.force_authenticate(user=self.client_user)
        payload = {
            "reported_user_id": self.phleb_user.id,
            "reason": "Harassment",
            "additional_details": "Sent inappropriate messages",
            "job_id": self.job.id
        }
        response = self.client.post(self.report_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], "Report submitted successfully.")
        self.assertEqual(data['data']['reason'], "harassment")
        self.assertEqual(data['data']['job_id'], self.job.id)

    def test_post_report_user_success_without_job(self):
        self.client.force_authenticate(user=self.phleb_user)
        payload = {
            "reported_user_id": self.client_user.id,
            "reason": "Spam",
            "additional_details": "Spamming job inquiries"
        }
        response = self.client.post(self.report_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['job_id'], None)
        self.assertEqual(data['data']['reason'], "spam")


class PhlebotomistHomeAPIViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job, JobAssignment
        from authentication.models import Phlebotomist
        import datetime

        # Client user
        self.client_user = User.objects.create_user(
            email="client_home@example.com",
            password="SecurePassword123!",
            full_name="Client User",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )

        # Phlebotomist user
        self.phleb_user = User.objects.create_user(
            email="phleb_home@example.com",
            password="SecurePassword123!",
            full_name="Phleb User",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        self.phleb_profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number="LIC-999999",
            license_expiry_date=datetime.date(2030, 8, 15),
            years_of_experience=5,
            specialty=Phlebotomist.GENERAL_PHLEBOTOMY,
            work_preference=Phlebotomist.FULL_TIME,
            service_area="New York",
            approved=True
        )

        # Job
        self.job = Job.objects.create(
            client=self.client_user,
            title="Blood Draw Station",
            description="Perform venipuncture.",
            location="General Hospital, Room 205",
            city="Dhaka",
            shift_date=datetime.date.today(),
            shift_start=datetime.time(14, 30),
            shift_end=datetime.time(15, 0),
            shift_duration=1,
            pay_type="hourly",
            pay_rate=50.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        # JobAssignment
        self.assignment = JobAssignment.objects.create(
            job=self.job,
            phlebotomist=self.phleb_user,
            client=self.client_user,
            status=JobAssignment.ACTIVE,
            signed_by_phlebotomist=True
        )

        self.home_url = reverse('phlebotomist-home')

    def test_phlebotomist_home_success(self):
        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['user']['full_name'], "Phleb User")
        self.assertEqual(data['data']['metrics']['pending_payouts'], "$ 40")
        self.assertEqual(data['data']['next_job']['title'], "Blood Draw Station")
        self.assertEqual(data['data']['next_job']['location'], "General Hospital, Room 205")
        self.assertEqual(data['data']['license_expiration']['expiry_date'], "15 August 2030")


class ClientHomeAPIViewTests(APITestCase):

    def setUp(self):
        from jobs.models import Job, JobAssignment
        from appointments.models import Appointment, PatientProfile, ServicePackage
        from communication.models import Notification
        import datetime

        # Client user
        self.client_user = User.objects.create_user(
            email="client_home_test@example.com",
            password="SecurePassword123!",
            full_name="Dr. Ratul",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )
        from authentication.models import Client
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

        # Create PatientProfile & ServicePackage for appointment
        self.patient = PatientProfile.objects.create(
            first_name="John",
            last_name="Doe",
            email="patient@example.com",
            phone_number="9876543210",
            gender="male",
            dob="1995-05-05"
        )
        self.service = ServicePackage.objects.create(
            name="General Blood Test",
            description="Routine test",
            price=150.00
        )

        # Create Appointment assigned to client, no job created yet
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            client=self.client_user,
            service_package=self.service,
            appointment_date=datetime.date.today(),
            start_time=datetime.time(10, 0),
            location_type="home",
            location="123 Road",
            status=Appointment.PENDING
        )

        # Create Job created by client, no phlebotomist assigned
        self.job = Job.objects.create(
            client=self.client_user,
            title="Blood Collection job",
            description="Perform venipuncture.",
            location="Patient address",
            city="Dhaka",
            shift_date=datetime.date.today(),
            shift_start=datetime.time(14, 30),
            shift_end=datetime.time(15, 0),
            shift_duration=1,
            pay_type="hourly",
            pay_rate=50.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        # Clear any auto-generated notifications from signals
        Notification.objects.filter(user=self.client_user).delete()

        # Create Notification
        self.notification = Notification.objects.create(
            user=self.client_user,
            title="New Message",
            message="Dr. Smith replied to your request",
            type="message",
            is_read=False
        )

        self.home_url = reverse('client-home')

    def test_client_home_success(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['user']['name'], "Dr. Ratul")
        
        # Verify dashboard overview metrics
        # pending_assignments: 1 (our job, since assignment__isnull=True)
        # new_applications: 1 (our appointment, since jobs__isnull=True)
        self.assertEqual(data['data']['metrics']['pending_assignments'], 1)
        self.assertEqual(data['data']['metrics']['new_applications'], 1)

        # Verify recent notifications
        self.assertEqual(len(data['data']['recent_notifications']), 1)
        self.assertEqual(data['data']['recent_notifications'][0]['title'], "New Message")
        self.assertEqual(data['data']['recent_notifications'][0]['message'], "Dr. Smith replied to your request")
        self.assertEqual(data['data']['recent_notifications'][0]['time'], "0s")

    def test_client_pending_appointments_success(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-pending-appointments')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['id'], self.appointment.id)
        self.assertEqual(data['data'][0]['patient']['first_name'], "John")
        self.assertEqual(data['data'][0]['service_package']['name'], "General Blood Test")

    def test_client_appointment_detail_success(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-appointment-detail', kwargs={'pk': self.appointment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['id'], self.appointment.id)
        self.assertEqual(data['data']['patient']['first_name'], "John")
        self.assertTrue(data['data']['patient']['patient_id'].endswith(f"-{self.patient.id:04d}"))
        self.assertEqual(data['data']['service_details']['name'], "General Blood Test")
        self.assertEqual(data['data']['location']['type'], "Patient's Home")

    def test_client_find_phlebotomist_no_job(self):
        from authentication.models import Phlebotomist, PhlebotomistAvailability
        
        # Create a phlebotomist user
        phleb_user = User.objects.create_user(
            email="phleb_test_find@example.com",
            password="SecurePassword123!",
            full_name="John Phlebotomist",
            phone_number="1212121212",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        
        profile = Phlebotomist.objects.create(
            user=phleb_user,
            license_number="LIC-12345",
            license_expiry_date="2028-01-01",
            years_of_experience=4,
            specialty="general_phlebotomy",
            work_preference="full_time",
            service_area="Dallas"
        )
        
        # Add availability slot
        PhlebotomistAvailability.objects.create(
            phlebotomist=profile,
            day="Monday",
            date=datetime.date.today(),
            start_time=datetime.time(9, 0),
            end_time=datetime.time(17, 0),
            is_available=True
        )

        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-find-phlebotomist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertIn('pagination', data)
        self.assertIn('results', data)
        
        # Find our created phlebotomist in results
        results = data['results']
        phleb_data = next((item for item in results if item['id'] == phleb_user.id), None)
        self.assertIsNotNone(phleb_data)
        self.assertEqual(phleb_data['availability_status'], "Available")
        self.assertEqual(phleb_data['full_name'], "John Phlebotomist")

    def test_client_find_phlebotomist_with_job(self):
        from authentication.models import Phlebotomist, PhlebotomistAvailability
        import datetime

        # Phlebotomist 1: Perfect match (matching specialty and availability)
        phleb_user_1 = User.objects.create_user(
            email="phleb1_test_find@example.com",
            password="SecurePassword123!",
            full_name="Phleb Match",
            phone_number="1111111111",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        
        # Job has professional_type = Job.CERTIFIED_PHLEBOTOMIST (CP)
        # Specialty general_phlebotomy matches CP
        profile_1 = Phlebotomist.objects.create(
            user=phleb_user_1,
            license_number="LIC-11111",
            license_expiry_date="2028-01-01",
            years_of_experience=10,
            specialty="general_phlebotomy",
            work_preference="full_time",
            service_area="Dallas"
        )
        
        # Availability overlaps job shift time (14:30 - 15:00)
        PhlebotomistAvailability.objects.create(
            phlebotomist=profile_1,
            day="Monday",
            date=self.job.shift_date,
            start_time=datetime.time(13, 0),
            end_time=datetime.time(16, 0),
            is_available=True
        )

        # Phlebotomist 2: Poor match (no matching availability, different specialty)
        phleb_user_2 = User.objects.create_user(
            email="phleb2_test_find@example.com",
            password="SecurePassword123!",
            full_name="Phleb NoMatch",
            phone_number="2222222222",
            gender="female",
            dob="1992-02-02",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        profile_2 = Phlebotomist.objects.create(
            user=phleb_user_2,
            license_number="LIC-22222",
            license_expiry_date="2028-01-01",
            years_of_experience=1,
            specialty="medical_nurse",
            work_preference="part_time",
            service_area="Dallas"
        )

        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-find-phlebotomist')
        response = self.client.get(f"{url}?job_id={self.job.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        
        results = data['results']
        self.assertTrue(len(results) >= 2)
        self.assertEqual(results[0]['id'], phleb_user_1.id)
        self.assertTrue(results[0]['match_percentage'] > results[1]['match_percentage'])

    def test_client_appointment_trends_success(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-analytics-trends')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertIn('trends', data['data'])
        self.assertIn('peak_day', data['data'])
        self.assertIn('staff_performance', data['data'])
        self.assertIn('service_demand', data['data'])

        self.assertEqual(len(data['data']['trends']), 7)
        self.assertTrue(any(sp['name'] == "Sarah Johnson" for sp in data['data']['staff_performance']))
        self.assertTrue(any(sd['service_name'] == "Blood Draws" for sd in data['data']['service_demand']))
    def test_client_jobs_history_billing_success(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-jobs-history-billing')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) > 0)
        self.assertTrue(data['results'][0]['invoice_url'].startswith('http'))

        
        # Test filters
        response_paid = self.client.get(f"{url}?filter=paid")
        self.assertEqual(response_paid.status_code, status.HTTP_200_OK)
        for item in response_paid.data['results']:
            self.assertEqual(item['status'], "Paid")
            
        response_pending = self.client.get(f"{url}?filter=pending")
        self.assertEqual(response_pending.status_code, status.HTTP_200_OK)
        for item in response_pending.data['results']:
            self.assertEqual(item['status'], "Pending")

    def test_client_job_invoice_pdf_success(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-job-invoice', args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(len(response.content) > 0)

    def test_client_job_detail_mock_success(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-job-detail', args=["JB-2025-0315"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], "JB-2025-0315")
        self.assertEqual(response.data["assigned_phlebotomist"]["name"], "FA Kabita")
        self.assertEqual(response.data["job_description"]["title"], "Blood Draw Station")

    def test_client_job_detail_real_success(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-job-detail', args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.job.id)
        self.assertIn("job_status", response.data)
        self.assertIn("assigned_phlebotomist", response.data)
        self.assertIn("payment_details", response.data)

    def test_client_job_pay_real_success(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-job-pay', args=[self.job.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("checkout_url", response.data)

    def test_create_job_review_success(self):
        # Create and assign a phlebotomist to the job first
        phleb_user = User.objects.create_user(
            email="phleb_review_test@example.com",
            password="SecurePassword123!",
            full_name="FA Kabita",
            phone_number="1112223333",
            gender="female",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )
        from authentication.models import Phlebotomist
        Phlebotomist.objects.create(
            user=phleb_user,
            license_number="LIC-12345",
            license_expiry_date="2030-01-01",
            years_of_experience=5,
            specialty="general_phlebotomy",
            work_preference="full_time",
            service_area="Dallas"
        )
        from jobs.models import JobAssignment
        JobAssignment.objects.create(
            job=self.job,
            phlebotomist=phleb_user,
            client=self.client_user,
            status=JobAssignment.ACTIVE
        )

        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-job-review', args=[self.job.id])
        payload = {
            "rating": 4,
            "comment": "Nice job!"
        }
        response = self.client.post(url, data=payload, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(response.data["success"])
        
        # Verify the review details in the detail response
        detail_url = reverse('client-job-detail', args=[self.job.id])
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertTrue(detail_response.data["review"]["has_reviewed"])
        self.assertEqual(detail_response.data["review"]["rating"], 4)
        self.assertEqual(detail_response.data["review"]["comment"], "Nice job!")


class PhlebotomistClientListToReportAPITests(APITestCase):

    def setUp(self):
        # Create Phlebotomist user
        self.phleb_user = User.objects.create_user(
            email="phleb_rep_list@example.com",
            password="SecurePassword123!",
            full_name="Phleb Rep List",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )

        # Create Client user 1 (has worked with phlebotomist)
        self.client_user1 = User.objects.create_user(
            email="client_rep_list1@example.com",
            password="SecurePassword123!",
            full_name="Client Rep List A",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )

        # Create Client user 2 (has NOT worked with phlebotomist)
        self.client_user2 = User.objects.create_user(
            email="client_rep_list2@example.com",
            password="SecurePassword123!",
            full_name="Client Rep List B",
            phone_number="1234567892",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )

        # Create a Job with Client 1
        from jobs.models import Job, JobAssignment
        import datetime
        self.job = Job.objects.create(
            client=self.client_user1,
            title="Blood Draw",
            description="Regular blood draw service.",
            location="123 Main Street, New York",
            city="New York",
            shift_date=datetime.date.today(),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(17, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        # Create assignment for this phlebotomist
        JobAssignment.objects.create(
            job=self.job,
            phlebotomist=self.phleb_user,
            client=self.client_user1,
            status=JobAssignment.ACTIVE
        )

        self.list_url = reverse('phlebotomist-clients-report')

    def test_get_client_list_success(self):
        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertTrue(data['success'])
        
        clients = data['data']['clients']
        # Should contain both client_user1 and client_user2
        self.assertEqual(len(clients), 2)
        
        # Client 1 should be first because the phlebotomist worked with them
        self.assertEqual(clients[0]['id'], self.client_user1.id)
        self.assertEqual(clients[0]['name'], "Client Rep List A")
        self.assertEqual(clients[1]['id'], self.client_user2.id)
        self.assertEqual(clients[1]['name'], "Client Rep List B")

    def test_get_client_list_unauthorized(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class InvitePhlebotomistToTheJobTests(APITestCase):

    def setUp(self):
        self.client_user = User.objects.create_user(
            email="client_invite_test@example.com",
            password="SecurePassword123!",
            full_name="Client User",
            phone_number="1234567890",
            gender="male",
            dob="1980-01-01",
            role=User.CLIENT,
            is_active=True
        )
        # Create client profile to pass IsApprovedClient
        from authentication.models import Client
        Client.objects.create(
            client=self.client_user,
            business_name="Test Business",
            business_type=Client.HEALTHCARE,
            business_address_street="123 Main St",
            business_address_city="New York",
            business_address_state="NY",
            business_address_zip="10001",
            contact_person_name="Contact Person",
            business_phone="1234567890",
            business_license_number="LIC123",
            business_description="Test Business Description",
            hourly_pay_rate=30.00,
            preferred_job_type=Client.MOBILE_BLOOD_DRAW,
            work_preference=Client.FULL_TIME,
            is_approved=True
        )

        self.phleb_user = User.objects.create_user(
            email="phleb_invite_test@example.com",
            password="SecurePassword123!",
            full_name="Phlebotomist User",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST,
            is_active=True
        )

        from jobs.models import Job
        import datetime
        self.job = Job.objects.create(
            id="JB-25-100001",
            client=self.client_user,
            title="Blood Draw Test",
            description="Regular blood draw service.",
            location="123 Main Street, New York",
            city="New York",
            shift_date=datetime.date.today(),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(17, 0),
            shift_duration=8,
            pay_type="hourly",
            pay_rate=30.00,
            status=Job.APPROVED,
            job_type=Job.URGENT
        )

        self.invite_url = reverse('invite-phlebotomist-to-job', kwargs={'user_id': self.phleb_user.id})

    def test_invite_phlebotomist_success(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.post(self.invite_url, data={'job_id': self.job.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("Successfully invited", response.data['message'])

        # Verify JobAssignment is created in PENDING status
        from jobs.models import JobAssignment, JobApplication
        assignment = JobAssignment.objects.filter(job=self.job).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.status, JobAssignment.PENDING)
        self.assertEqual(assignment.phlebotomist, self.phleb_user)

        # Verify JobApplication is ACCEPTED
        app = JobApplication.objects.filter(job=self.job, phlebotomist=self.phleb_user).first()
        self.assertIsNotNone(app)
        self.assertEqual(app.status, JobApplication.ACCEPTED)

    def test_invite_phlebotomist_unauthorized(self):
        response = self.client.post(self.invite_url, data={'job_id': self.job.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
















