import datetime
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from rest_framework.test import APITestCase
from rest_framework import status

from communication.models import Notification, Message, Report
from authentication.models import Phlebotomist, Client
from jobs.models import Job, JobAssignment, JobApplication
from appointments.models import Appointment, PatientProfile, ServicePackage, Payment, PayoutRequest

User = get_user_model()

class NotificationAPITests(APITestCase):
    def setUp(self):
        # Create users
        self.user = User.objects.create_user(
            email='testuser@example.com',
            full_name='Test User',
            role='phlebotomist',
            password='Password123!',
            phone_number='1234567890',
            gender='male',
            dob=datetime.date(1990, 1, 1)
        )
        self.client.force_authenticate(user=self.user)
        
        # Create notifications
        self.n1 = Notification.objects.create(
            user=self.user,
            title='Job Assigned',
            message='You have been assigned a job.',
            type='job_alert',
            is_read=False
        )
        self.n2 = Notification.objects.create(
            user=self.user,
            title='Payment Received',
            message='Payment of $100 received.',
            type='payment',
            is_read=True
        )
        
    def test_list_notifications(self):
        url = reverse('notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 2)
        
        # Filter by read status
        response = self.client.get(url, {'is_read': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['id'], self.n2.id)

        response = self.client.get(url, {'is_read': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['id'], self.n1.id)

    def test_unread_count(self):
        url = reverse('notification-unread-count')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['unread_count'], 1)

    def test_mark_read_single(self):
        url = reverse('notification-mark-read')
        response = self.client.post(url, {'notification_id': self.n1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_mark_read_all(self):
        url = reverse('notification-mark-read')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.n1.refresh_from_db()
        self.n2.refresh_from_db()
        self.assertTrue(self.n1.is_read)
        self.assertTrue(self.n2.is_read)

    def test_register_fcm_device(self):
        url = reverse('devices-list')
        data = {
            'registration_id': 'fcm_token_example_123',
            'type': 'android',
            'name': 'My Android Device'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        from fcm_django.models import FCMDevice
        self.assertTrue(FCMDevice.objects.filter(user=self.user, registration_id='fcm_token_example_123').exists())



class NotificationSignalTests(APITestCase):
    def setUp(self):
        # Create admin
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            full_name='Admin User',
            role='admin',
            password='Password123!',
            phone_number='1111111111',
            gender='male',
            dob=datetime.date(1985, 1, 1)
        )
        
        # Create client and phlebotomist users
        self.phleb_user = User.objects.create_user(
            email='phleb@example.com',
            full_name='FA Kabita',
            role='phlebotomist',
            password='Password123!',
            phone_number='2222222222',
            gender='female',
            dob=datetime.date(1995, 1, 1)
        )
        self.client_user = User.objects.create_user(
            email='client@example.com',
            full_name='Sarah Connor',
            role='client',
            password='Password123!',
            phone_number='3333333333',
            gender='female',
            dob=datetime.date(1988, 1, 1)
        )

    def test_phlebotomist_profile_approved_signal(self):
        mail.outbox.clear()
        
        # Create profile (by default approved=None or False)
        profile = Phlebotomist.objects.create(
            user=self.phleb_user,
            license_number='LIC-12345',
            license_expiry_date=datetime.date.today(),
            years_of_experience=3,
            specialty='general_phlebotomy',
            work_preference='full_time',
            service_area='San Jose',
            approved=None
        )
        
        # Verify no approval notification yet
        self.assertFalse(Notification.objects.filter(user=self.phleb_user, type='account_status').exists())
        
        # Approve the profile
        profile.approved = True
        profile.save()
        
        # Verify notification and email
        self.assertTrue(Notification.objects.filter(user=self.phleb_user, type='account_status').exists())
        notification = Notification.objects.get(user=self.phleb_user, type='account_status')
        self.assertIn("approved", notification.message)
        
        # Verify mail in outbox
        self.assertTrue(len(mail.outbox) > 0)
        self.assertEqual(mail.outbox[-1].subject, "Account Approved")

    def test_client_profile_approved_signal(self):
        mail.outbox.clear()
        
        # Create profile (by default is_approved=None or False)
        profile = Client.objects.create(
            client=self.client_user,
            business_name='Clinic XYZ',
            business_type='healthcare',
            business_address_street='123 Main St',
            business_address_city='San Jose',
            business_address_state='CA',
            business_address_zip='95112',
            contact_person_name='Sarah Connor',
            business_phone='1234567890',
            business_license_number='LIC-999',
            business_description='Clinic description',
            hourly_pay_rate=25.00,
            preferred_job_type='in_clinic_phlebotomy',
            work_preference='full_time',
            is_approved=None
        )
        
        # Verify no approval notification yet
        self.assertFalse(Notification.objects.filter(user=self.client_user, type='account_status').exists())
        
        # Approve the profile
        profile.is_approved = True
        profile.save()
        
        # Verify notification
        self.assertTrue(Notification.objects.filter(user=self.client_user, type='account_status').exists())
        
        # Verify mail in outbox
        self.assertTrue(len(mail.outbox) > 0)
        self.assertEqual(mail.outbox[-1].subject, "Account Approved")

    def test_job_signals(self):
        # Create job
        job = Job.objects.create(
            client=self.client_user,
            title='Morning Blood Draw',
            description='Shift details here',
            location='San Jose',
            pay_rate=25.00,
            shift_duration=4,
            shift_date=datetime.date.today(),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(13, 0),
            status=Job.OPEN
        )
        
        # Assign job
        assignment = JobAssignment.objects.create(
            job=job,
            phlebotomist=self.phleb_user,
            client=self.client_user,
            status=JobAssignment.PENDING
        )
        
        # Verify "Job Assigned" notification to Phlebotomist
        self.assertTrue(Notification.objects.filter(user=self.phleb_user, type='job_alert').exists())
        n_assign = Notification.objects.get(user=self.phleb_user, type='job_alert')
        self.assertIn("assigned", n_assign.message)
        
        # Accept assignment
        assignment.status = JobAssignment.ACTIVE
        assignment.save()
        
        # Verify "Job Accepted" notification to Client
        self.assertTrue(Notification.objects.filter(user=self.client_user, title="Job Accepted").exists())
        
        # Complete assignment
        assignment.status = JobAssignment.COMPLETED
        assignment.save()
        
        # Verify "Job Completed" notification to Client
        self.assertTrue(Notification.objects.filter(user=self.client_user, title="Job Completed").exists())

    def test_job_assignment_deleted_signal(self):
        job = Job.objects.create(
            client=self.client_user,
            title='Morning Blood Draw',
            description='Shift details here',
            location='San Jose',
            pay_rate=25.00,
            shift_duration=4,
            shift_date=datetime.date.today(),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(13, 0),
            status=Job.OPEN
        )
        
        assignment = JobAssignment.objects.create(
            job=job,
            phlebotomist=self.phleb_user,
            client=self.client_user,
            status=JobAssignment.PENDING
        )
        
        # Clear outbox/notifications before deletion
        Notification.objects.all().delete()
        
        # Delete assignment (decline)
        assignment.delete()
        
        # Verify client is notified of decline
        self.assertTrue(Notification.objects.filter(user=self.client_user, type='job_alert', title="Job Declined").exists())

    def test_job_application_signals(self):
        job = Job.objects.create(
            client=self.client_user,
            title='Morning Blood Draw',
            description='Shift details here',
            location='San Jose',
            pay_rate=25.00,
            shift_duration=4,
            shift_date=datetime.date.today(),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(13, 0),
            status=Job.OPEN
        )
        
        # Apply for job
        application = JobApplication.objects.create(
            job=job,
            phlebotomist=self.phleb_user,
            status=JobApplication.PENDING
        )
        
        # Verify client notification
        self.assertTrue(Notification.objects.filter(user=self.client_user, type='application_update', title="New Application").exists())
        
        # Accept application
        application.status = JobApplication.ACCEPTED
        application.save()
        
        # Verify phlebotomist notification
        self.assertTrue(Notification.objects.filter(user=self.phleb_user, type='application_update', title="Application Update").exists())

    def test_payment_received_signal(self):
        job = Job.objects.create(
            client=self.client_user,
            title='Morning Blood Draw',
            description='Shift details here',
            location='San Jose',
            pay_rate=25.00,
            shift_duration=4,
            shift_date=datetime.date.today(),
            shift_start=datetime.time(9, 0),
            shift_end=datetime.time(13, 0),
            status=Job.OPEN
        )
        
        assignment = JobAssignment.objects.create(
            job=job,
            phlebotomist=self.phleb_user,
            client=self.client_user,
            status=JobAssignment.ACTIVE
        )
        
        payment = Payment.objects.create(
            job=job,
            amount=100.00,
            payment_status=Payment.PENDING
        )
        
        # Set payment status to PAID
        payment.payment_status = Payment.PAID
        payment.save()
        
        # Verify phlebotomist received payment notification
        self.assertTrue(Notification.objects.filter(user=self.phleb_user, type='payment', title="Payment Received").exists())

    def test_payout_request_signals(self):
        # Request payout
        payout = PayoutRequest.objects.create(
            user=self.phleb_user,
            amount=50.00,
            status=PayoutRequest.PENDING
        )
        
        # Verify admin received financial alert
        self.assertTrue(Notification.objects.filter(user=self.admin, type='financial_alert', title="Payout Requested").exists())
        
        # Complete payout
        payout.status = PayoutRequest.COMPLETED
        payout.save()
        
        # Verify phlebotomist received status update
        self.assertTrue(Notification.objects.filter(user=self.phleb_user, type='payout_status', title="Payout Status Update").exists())

    def test_message_created_signal(self):
        # Create message
        Message.objects.create(
            sender=self.client_user,
            receiver=self.phleb_user,
            message_text='Hello there'
        )
        
        # Verify phlebotomist received message notification
        self.assertTrue(Notification.objects.filter(user=self.phleb_user, type='message', title="New Message").exists())

    def test_appointment_created_signal(self):
        # Create package and patient
        pkg = ServicePackage.objects.create(
            name='Test Package',
            price=99.00
        )
        patient = PatientProfile.objects.create(
            first_name='Bruce',
            last_name='Wayne',
            email='bruce@wayne.com',
            phone_number='1234567890',
            dob=datetime.date(1990, 1, 1),
            gender='male'
        )
        
        # Create appointment
        Appointment.objects.create(
            patient=patient,
            client=self.client_user,
            service_package=pkg,
            appointment_date=datetime.date.today(),
            start_time=datetime.time(9, 0),
            location='San Jose',
            status=Appointment.PENDING
        )
        
        # Verify client received booking notification
        self.assertTrue(Notification.objects.filter(user=self.client_user, type='appointment_update', title="Appointment Booked").exists())

    def test_user_otp_signal(self):
        mail.outbox.clear()
        
        # Update user OTP
        self.phleb_user.otp = '123456'
        self.phleb_user.save()
        
        # Verify OTP email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("123456", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].subject, "Verification OTP")

    def test_report_created_signal(self):
        # Create report
        Report.objects.create(
            reporter=self.client_user,
            reported_user=self.phleb_user,
            reason=Report.HARASSMENT,
            additional_details='Some harassment description'
        )
        
        # Verify admin received moderation alert
        self.assertTrue(Notification.objects.filter(user=self.admin, type='moderation_alert', title="Moderation Alert").exists())
