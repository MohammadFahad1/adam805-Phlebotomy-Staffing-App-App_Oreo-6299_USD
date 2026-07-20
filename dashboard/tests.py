from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
import datetime
from jobs.models import Job, JobAssignment
from authentication.models import Client, Phlebotomist

User = get_user_model()

class AssignPhlebotomistAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="clientpassword",
            full_name="Client User",
            phone_number="1234567891",
            gender="female",
            dob="1990-01-01",
            role=User.CLIENT
        )
        self.phlebotomist_user = User.objects.create_user(
            email="phleb@example.com",
            password="phlebpassword",
            full_name="John Phleb",
            phone_number="1234567892",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST
        )

        # Create job 1 (the one we want to assign)
        self.job1 = Job.objects.create(
            client=self.client_user,
            title="Job 1",
            description="Blood draw job 1",
            location="123 Main St",
            shift_date=datetime.date.today(),
            shift_start=datetime.time(9, 0, 0),
            shift_end=datetime.time(11, 0, 0),
            pay_rate=150.00,
            status=Job.APPROVED
        )

    def test_assign_phlebotomist_success(self):
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('job-management-assign', kwargs={'job_id': self.job1.id})
        
        response = self.client.patch(url, {'user_id': self.phlebotomist_user.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify job and assignment status
        self.job1.refresh_from_db()
        self.assertEqual(self.job1.status, Job.IN_PROGRESS)
        
        assignment = JobAssignment.objects.get(job=self.job1)
        self.assertEqual(assignment.phlebotomist, self.phlebotomist_user)
        self.assertEqual(assignment.status, JobAssignment.ACTIVE)

    def test_assign_phlebotomist_fails_when_busy_overlapping(self):
        # Create an existing job assignment that overlaps
        busy_job = Job.objects.create(
            client=self.client_user,
            title="Busy Job",
            description="Overlapping job",
            location="456 Other St",
            shift_date=datetime.date.today(),
            shift_start=datetime.time(10, 0, 0),  # overlaps with 9-11
            shift_end=datetime.time(12, 0, 0),
            pay_rate=150.00,
            status=Job.IN_PROGRESS
        )
        JobAssignment.objects.create(
            job=busy_job,
            phlebotomist=self.phlebotomist_user,
            client=self.client_user,
            status=JobAssignment.ACTIVE
        )

        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('job-management-assign', kwargs={'job_id': self.job1.id})
        
        response = self.client.patch(url, {'user_id': self.phlebotomist_user.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Phlebotomist is already scheduled for another active job at this time.", response.data['detail'])

    def test_assign_phlebotomist_success_same_day_no_overlap(self):
        # Create an existing job assignment on the same day but different time
        non_overlapping_job = Job.objects.create(
            client=self.client_user,
            title="Non-overlapping Job",
            description="Same day, different time",
            location="456 Other St",
            shift_date=datetime.date.today(),
            shift_start=datetime.time(12, 0, 0),  # no overlap (12-14 vs 9-11)
            shift_end=datetime.time(14, 0, 0),
            pay_rate=150.00,
            status=Job.IN_PROGRESS
        )
        JobAssignment.objects.create(
            job=non_overlapping_job,
            phlebotomist=self.phlebotomist_user,
            client=self.client_user,
            status=JobAssignment.ACTIVE
        )

        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('job-management-assign', kwargs={'job_id': self.job1.id})
        
        response = self.client.patch(url, {'user_id': self.phlebotomist_user.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_assign_phlebotomist_success_different_day_same_time(self):
        # Create an existing job assignment at same time but on a different day
        different_day_job = Job.objects.create(
            client=self.client_user,
            title="Different Day Job",
            description="Same time, different day",
            location="456 Other St",
            shift_date=datetime.date.today() + datetime.timedelta(days=1),
            shift_start=datetime.time(9, 0, 0),
            shift_end=datetime.time(11, 0, 0),
            pay_rate=150.00,
            status=Job.IN_PROGRESS
        )
        JobAssignment.objects.create(
            job=different_day_job,
            phlebotomist=self.phlebotomist_user,
            client=self.client_user,
            status=JobAssignment.ACTIVE
        )

        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('job-management-assign', kwargs={'job_id': self.job1.id})
        
        response = self.client.patch(url, {'user_id': self.phlebotomist_user.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DisputeManagementStatisticsAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="clientpassword",
            full_name="Client User",
            phone_number="1234567891",
            gender="female",
            dob="1990-01-01",
            role=User.CLIENT
        )
        self.phlebotomist_user = User.objects.create_user(
            email="phleb@example.com",
            password="phlebpassword",
            full_name="John Phleb",
            phone_number="1234567892",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST
        )

    def test_statistics_when_db_empty(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dispute-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify statistics return 0 when database has no reports
        self.assertEqual(response.data['pending_issues'], 0)
        self.assertEqual(response.data['under_review'], 0)
        self.assertEqual(response.data['resolved_today'], 0)

    def test_statistics_actual_db_counts(self):
        from communication.models import Report
        from django.utils import timezone
        
        # Create some reports
        # Pending
        for _ in range(3):
            Report.objects.create(
                reporter=self.client_user,
                reported_user=self.phlebotomist_user,
                reason=Report.HARASSMENT,
                status=Report.PENDING
            )
        # Reviewed
        for _ in range(2):
            Report.objects.create(
                reporter=self.client_user,
                reported_user=self.phlebotomist_user,
                reason=Report.HARASSMENT,
                status=Report.REVIEWED
            )
        # Resolved
        for _ in range(4):
            Report.objects.create(
                reporter=self.client_user,
                reported_user=self.phlebotomist_user,
                reason=Report.HARASSMENT,
                status=Report.RESOLVED,
                resolved_at=timezone.now()
            )

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dispute-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify database counts are returned instead of fallbacks
        self.assertEqual(response.data['pending_issues'], 3)
        self.assertEqual(response.data['under_review'], 2)
        self.assertEqual(response.data['resolved_today'], 4)

    def test_statistics_permissions_denied_for_non_admin(self):
        # Unauthenticated
        url = reverse('dispute-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Non-admin
        self.client.force_authenticate(user=self.phlebotomist_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DisputeManagementListAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="clientpassword",
            full_name="FA Kabita",
            phone_number="1234567891",
            gender="female",
            dob="1990-01-01",
            role=User.CLIENT
        )
        self.phlebotomist_user = User.objects.create_user(
            email="phleb@example.com",
            password="phlebpassword",
            full_name="John Phleb",
            phone_number="1234567892",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST
        )

        from communication.models import Report
        # Create 3 reports corresponding to the screenshot
        self.r1 = Report.objects.create(
            reporter=self.client_user,
            reported_user=self.phlebotomist_user,
            reason=Report.OTHER,
            status=Report.RESOLVED
        )
        self.r2 = Report.objects.create(
            reporter=self.client_user,
            reported_user=self.phlebotomist_user,
            reason=Report.INAPPROPRIATE_LANGUAGE,
            status=Report.RESOLVED
        )
        self.r3 = Report.objects.create(
            reporter=self.client_user,
            reported_user=self.phlebotomist_user,
            reason=Report.HARASSMENT,
            status=Report.PENDING
        )

    def test_list_all_disputes(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dispute-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify success structure and paginated format
        self.assertTrue(response.data['success'])
        results = response.data['results']
        self.assertEqual(len(results), 3)

        # Check detail matching figma
        first_item = results[0]  # ordered by -created_at, so r3 is first
        self.assertEqual(first_item['title'], 'Harassment Report')
        self.assertEqual(first_item['reported_by'], 'FA Kabita')
        self.assertEqual(first_item['priority'], 'High')
        self.assertEqual(first_item['status_display'], 'Pending')
        self.assertEqual(first_item['case_id'], f"#HR-{self.r3.created_at.year}-{self.r3.id:03d}")

    def test_list_filtering_by_status(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dispute-list')
        
        # Filter status=solved (should return r1 and r2, resolved_today/solved maps to status='resolved')
        response = self.client.get(url, {'status': 'solved'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pagination']['count'], 2)

        # Filter status=pending (should return r3)
        response = self.client.get(url, {'status': 'pending'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pagination']['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Harassment Report')

    def test_list_filtering_by_issue_type(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dispute-list')

        # Filter by issue='Payment Issue' (maps to reason='other', i.e. r1)
        response = self.client.get(url, {'issue': 'Payment Issue'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pagination']['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Payment Issue')

    def test_list_permissions_denied(self):
        url = reverse('dispute-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.phlebotomist_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DisputeManagementDetailAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="clientpassword",
            full_name="FA Kabita",
            phone_number="1234567891",
            gender="female",
            dob="1990-01-01",
            role=User.CLIENT
        )
        self.phlebotomist_user = User.objects.create_user(
            email="phleb@example.com",
            password="phlebpassword",
            full_name="DR Ratul",
            phone_number="1234567892",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST
        )

        from communication.models import Report
        self.report = Report.objects.create(
            reporter=self.client_user,
            reported_user=self.phlebotomist_user,
            reason=Report.HARASSMENT,
            additional_details="User reported receiving inappropriate messages...",
            status=Report.PENDING
        )

    def test_get_report_details_figma_match(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dispute-detail', kwargs={'report_id': self.report.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert correct Figma field structure
        self.assertEqual(response.data['case_id'], f"#HR-{self.report.created_at.year}-{self.report.id:03d}")
        
        info = response.data['complaint_information']
        self.assertEqual(info['type'], 'Harassment & Inappropriate Behavior')
        self.assertEqual(info['filed_by'], 'FA Kabita')
        self.assertEqual(info['reported_user'], 'DR Ratul')
        self.assertEqual(info['platform'], 'Direct Messages')
        
        self.assertEqual(response.data['initial_report_summary'], 'User reported receiving inappropriate messages...')
        self.assertEqual(response.data['submitted_evidence'], [])
        
        decision = response.data['decision_summary']
        self.assertEqual(decision['admin_notes'], '')
        self.assertIn("Suspend User Account", decision['recommended_action'])

    def test_patch_report_decision_and_resolve(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dispute-detail', kwargs={'report_id': self.report.id})
        
        payload = {
            "status": "solved",
            "admin_notes": "Warning issued to DR Ratul."
        }
        response = self.client.patch(url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'resolved')
        self.assertEqual(self.report.admin_notes, 'Warning issued to DR Ratul.')
        self.assertIsNotNone(self.report.resolved_at)
        self.assertEqual(self.report.resolved_by, self.admin_user)

    def test_detail_permissions_denied(self):
        url = reverse('dispute-detail', kwargs={'report_id': self.report.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.phlebotomist_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TermsOfServiceAPITests(APITestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.phlebotomist_user = User.objects.create_user(
            email="phleb@example.com",
            password="phlebpassword",
            full_name="John Phleb",
            phone_number="1234567892",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST
        )

    def test_public_get_terms_of_service_creates_default(self):
        url = reverse('terms-of-service')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Primepath Service Agreement")
        self.assertIn("January 2025", response.data['description'])
        self.assertIn("1. Terms of Service", response.data['description'])

    def test_admin_create_terms_of_service(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-terms-of-service-list-create')
        payload = {
            "title": "New Agreement",
            "description": "Simple description text."
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], "New Agreement")

    def test_admin_list_terms_of_service(self):
        from dashboard.models import TermsOfService
        TermsOfService.objects.create(title="Existing", description="Some text")
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-terms-of-service-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['results']) >= 1)

    def test_admin_update_terms_of_service(self):
        from dashboard.models import TermsOfService
        terms = TermsOfService.objects.create(title="Old Title", description="Old description")
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-terms-of-service-detail', kwargs={'pk': terms.id})
        payload = {
            "title": "New Title",
            "description": "New description text."
        }
        response = self.client.put(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "New Title")

    def test_admin_delete_terms_of_service(self):
        from dashboard.models import TermsOfService
        terms = TermsOfService.objects.create(title="To Delete", description="To delete desc")
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-terms-of-service-detail', kwargs={'pk': terms.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TermsOfService.objects.filter(pk=terms.id).exists())

    def test_permissions_denied_for_non_admin(self):
        url_list = reverse('admin-terms-of-service-list-create')
        
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        self.client.force_authenticate(user=self.phlebotomist_user)
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ReviewsModerationAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="clientpassword",
            full_name="Client User",
            phone_number="1234567891",
            gender="female",
            dob="1990-01-01",
            role=User.CLIENT
        )
        self.phleb_user = User.objects.create_user(
            email="phleb@example.com",
            password="phlebpassword",
            full_name="John Phleb",
            phone_number="1234567892",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST
        )

        from jobs.models import Job
        # Create job
        self.job = Job.objects.create(
            client=self.client_user,
            title="Blood Draw Job",
            description="Perform blood draws.",
            location="123 Main St",
            shift_date=datetime.date.today(),
            shift_start=datetime.time(9, 0, 0),
            shift_end=datetime.time(11, 0, 0),
            pay_rate=150.00,
            status=Job.COMPLETED
        )

        from communication.models import Review
        # Create reviews
        # 1. Approved Review
        self.rev1 = Review.objects.create(
            job=self.job,
            reviewer=self.client_user,
            reviewed=self.phleb_user,
            rating=5,
            comment="Awesome work!",
            status=Review.APPROVED
        )
        # 2. Pending Review (should come first in list)
        self.rev2 = Review.objects.create(
            job=self.job,
            reviewer=self.client_user,
            reviewed=self.phleb_user,
            rating=4,
            comment="Good work, but pending moderation.",
            status=Review.PENDING
        )

        self.list_url = reverse('dashboard-reviews-list')

    def test_list_reviews_ordering_pending_first(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        self.assertEqual(len(results), 2)
        
        # Pending review (rev2) must be first
        self.assertEqual(results[0]['id'], self.rev2.id)
        self.assertEqual(results[0]['status'], 'pending')
        
        # Approved review (rev1) must be second
        self.assertEqual(results[1]['id'], self.rev1.id)
        self.assertEqual(results[1]['status'], 'approved')

    def test_get_review_detail(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dashboard-reviews-detail', kwargs={'pk': self.rev2.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comment'], "Good work, but pending moderation.")

    def test_patch_review_status(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dashboard-reviews-detail', kwargs={'pk': self.rev2.id})
        response = self.client.patch(url, {'status': 'approved'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.rev2.refresh_from_db()
        self.assertEqual(self.rev2.status, 'approved')

    def test_delete_review(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dashboard-reviews-detail', kwargs={'pk': self.rev2.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        from communication.models import Review
        self.assertFalse(Review.objects.filter(id=self.rev2.id).exists())

    def test_reviews_permissions_denied_for_non_admin(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.phleb_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserManagementEditAPITests(APITestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.phleb_user = User.objects.create_user(
            email="phleb@example.com",
            password="phlebpassword",
            full_name="John Phleb",
            phone_number="1234567892",
            gender="male",
            dob="1990-01-01",
            role=User.PHLEBOTOMIST
        )
        # Create Phlebotomist profile
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
        
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="clientpassword",
            full_name="Client User",
            phone_number="1234567891",
            gender="female",
            dob="1990-01-01",
            role=User.CLIENT
        )
        # Create Client profile
        self.client_profile = Client.objects.create(
            client=self.client_user,
            business_name="Original Clinic",
            business_type="healthcare",
            business_address_street="456 Avenue",
            business_address_city="NY",
            business_address_state="NY",
            business_address_zip="10001",
            contact_person_name="Jane Client",
            business_phone="9876543210",
            business_license_number="BL-123",
            business_description="Clinic",
            hourly_pay_rate=35.00,
            preferred_job_type="in_clinic_phlebotomy",
            work_preference="full_time",
            no_of_employees=10
        )

    def test_edit_phlebotomist_profile_success(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('user-management-edit', kwargs={'user_id': self.phleb_user.id})
        payload = {
            "full_name": "Updated John Phleb",
            "email": "updated_phleb@example.com",
            "license_number": "PHL-654321",
            "years_of_experience": 8,
            "skills": ["venipuncture", "capillary_puncture"],
            "availabilities": [
                {
                    "day": "Monday",
                    "date": "2025-09-01",
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "is_available": True
                }
            ]
        }
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.phleb_user.refresh_from_db()
        self.assertEqual(self.phleb_user.full_name, "Updated John Phleb")
        self.assertEqual(self.phleb_user.email, "updated_phleb@example.com")
        
        self.phleb_profile.refresh_from_db()
        self.assertEqual(self.phleb_profile.license_number, "PHL-654321")
        self.assertEqual(self.phleb_profile.years_of_experience, 8)
        self.assertEqual(self.phleb_profile.skills.count(), 2)
        self.assertEqual(self.phleb_profile.availabilities.count(), 1)

    def test_edit_client_profile_success(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('user-management-edit', kwargs={'user_id': self.client_user.id})
        payload = {
            "full_name": "Updated Client User",
            "business_name": "Updated Clinic LLC",
            "hourly_pay_rate": "45.50",
            "no_of_employees": 15,
            "availabilities": [
                {
                    "day": "Wednesday",
                    "date": "2025-09-03",
                    "start_time": "08:00",
                    "end_time": "16:00",
                    "is_available": True
                }
            ]
        }
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.full_name, "Updated Client User")
        
        self.client_profile.refresh_from_db()
        self.assertEqual(self.client_profile.business_name, "Updated Clinic LLC")
        self.assertEqual(float(self.client_profile.hourly_pay_rate), 45.50)
        self.assertEqual(self.client_profile.no_of_employees, 15)
        self.assertEqual(self.client_profile.availabilities.count(), 1)


class SuspendUserAccountAPITests(APITestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.target_user = User.objects.create_user(
            email="target@example.com",
            password="targetpassword",
            full_name="Target User",
            phone_number="1234567891",
            gender="male",
            dob="1990-01-01",
            role=User.CLIENT
        )

    def test_suspend_unsuspend_toggle(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('suspend-unsuspend', kwargs={'user_id': self.target_user.id})
        
        # Initial suspend
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.suspended)
        
        # Unsuspend toggle
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.suspended)

    def test_suspend_unsuspend_explicit(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('suspend-unsuspend', kwargs={'user_id': self.target_user.id})
        
        # Explicit suspend
        response = self.client.patch(url, {'suspended': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.suspended)
        
        # Sending explicit suspend = True again should stay True
        response = self.client.patch(url, {'suspended': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.suspended)
        
        # Explicit unsuspend
        response = self.client.patch(url, {'suspended': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.suspended)

    def test_self_suspension_prevented(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('suspend-unsuspend', kwargs={'user_id': self.admin_user.id})
        
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin_user.refresh_from_db()
        self.assertFalse(self.admin_user.suspended)


class ServicePackagesAPITests(APITestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            email="admin_packages@example.com",
            password="adminpassword",
            full_name="Admin Packages",
            phone_number="1234567810",
            gender="male",
            dob="1980-01-01",
            role=User.ADMIN
        )
        self.client_user = User.objects.create_user(
            email="client_packages@example.com",
            password="clientpassword",
            full_name="Client Packages",
            phone_number="1234567811",
            gender="female",
            dob="1990-01-01",
            role=User.CLIENT
        )
        from appointments.models import ServicePackage, ServicePackageFeature
        self.package = ServicePackage.objects.create(
            name="Premium Package",
            description="Premium package description",
            price=99.99
        )
        self.feature = ServicePackageFeature.objects.create(
            service_package=self.package,
            name="Feature 1"
        )
        self.list_url = reverse('service-packages')
        self.detail_url = reverse('service-package-detail', kwargs={'package_id': self.package.id})
        self.features_url = reverse('service-package-features')
        self.feature_detail_url = reverse('service-package-feature-detail', kwargs={'feature_id': self.feature.id})

    def test_get_service_packages(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Premium Package")

    def test_create_service_package(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "Standard Package",
            "description": "Standard package description",
            "price": 49.99,
            "features": ["Feature A", "Feature B"]
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Standard Package")
        
        from appointments.models import ServicePackage
        package = ServicePackage.objects.get(name="Standard Package")
        self.assertEqual(package.features.count(), 2)

    def test_update_service_package(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "Updated Premium Package",
            "price": 109.99,
            "features": ["Updated Feature 1", "Updated Feature 2"]
        }
        response = self.client.put(self.detail_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.package.refresh_from_db()
        self.assertEqual(self.package.name, "Updated Premium Package")
        self.assertEqual(float(self.package.price), 109.99)
        self.assertEqual(self.package.features.count(), 2)

    def test_delete_service_package(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        from appointments.models import ServicePackage
        self.assertFalse(ServicePackage.objects.filter(id=self.package.id).exists())

    def test_get_features(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.features_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_feature(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "New Feature",
            "service_package_id": self.package.id
        }
        response = self.client.post(self.features_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "New Feature")

    def test_update_feature(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "Renamed Feature 1"
        }
        response = self.client.put(self.feature_detail_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.feature.refresh_from_db()
        self.assertEqual(self.feature.name, "Renamed Feature 1")

    def test_delete_feature(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.feature_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        from appointments.models import ServicePackageFeature
        self.assertFalse(ServicePackageFeature.objects.filter(id=self.feature.id).exists())


class UserManagementDetailAPITests(APITestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin_detail@example.com",
            password="adminpassword",
            full_name="Admin User",
            phone_number="1234567890",
            gender="male",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.phleb_user = User.objects.create_user(
            email="phleb_detail@example.com",
            password="phlebpassword",
            full_name="John Phleb",
            phone_number="1234567892",
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
        self.client_user = User.objects.create_user(
            email="client_detail@example.com",
            password="clientpassword",
            full_name="Client User",
            phone_number="1234567891",
            gender="female",
            dob="1990-01-01",
            role=User.CLIENT
        )
        self.client_profile = Client.objects.create(
            client=self.client_user,
            business_name="Original Clinic",
            business_type="healthcare",
            business_address_street="456 Avenue",
            business_address_city="NY",
            business_address_state="NY",
            business_address_zip="10001",
            contact_person_name="Jane Client",
            business_phone="9876543210",
            business_license_number="BL-123",
            business_description="Clinic",
            hourly_pay_rate=35.00,
            preferred_job_type="in_clinic_phlebotomy",
            work_preference="full_time",
            no_of_employees=10
        )

    def test_get_user_management_detail_phlebotomist(self):
        # Create a completed job and assignment
        job = Job.objects.create(
            client=self.client_user,
            title="Blood Draw Job",
            description="Perform blood draws.",
            location="123 Main St",
            shift_date=datetime.date.today(),
            shift_start=datetime.time(9, 0, 0),
            shift_end=datetime.time(11, 0, 0),
            pay_rate=150.00,
            status=Job.COMPLETED
        )
        # Prevent Unique constraint error by creating job first, then assigning it
        assignment = JobAssignment.objects.create(
            job=job,
            phlebotomist=self.phleb_user,
            client=self.client_user,
            status='completed'
        )

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('user-management-detail', kwargs={'user_id': self.phleb_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['header']['full_name'], "John Phleb")
        self.assertEqual(response.data['activity_summary']['jobs_completed'], 1)
        self.assertNotEqual(response.data['activity_summary']['last_active'], "Never")

    def test_get_user_management_detail_client(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('user-management-detail', kwargs={'user_id': self.client_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['header']['full_name'], "Client User")






