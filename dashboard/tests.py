from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
import datetime
from jobs.models import Job, JobAssignment

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
