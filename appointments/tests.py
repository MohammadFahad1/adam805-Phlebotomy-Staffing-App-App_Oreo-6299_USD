from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from appointments.models import ServicePackage, PatientProfile, Appointment
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
import datetime

User = get_user_model()

class AppointmentAPITests(APITestCase):

    def setUp(self):
        # Create a test service package
        self.service_package = ServicePackage.objects.create(
            name="Basic Panel",
            description="Basic blood draw tests",
            price=89.00,
            is_active=True
        )
        # Create a standard user for authentication tests
        self.phlebotomist_user = User.objects.create_user(
            email="phleb@example.com",
            password="testpassword123",
            full_name="John Phleb",
            phone_number="1234567890",
            gender="male",
            dob="1995-01-01",
            role=User.PHLEBOTOMIST
        )
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="testpassword123",
            full_name="Admin User",
            phone_number="0987654321",
            gender="female",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )

    def test_list_service_packages(self):
        url = reverse('service-package-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify package is listed
        names = [pkg['name'] for pkg in response.data['results']]
        self.assertIn("Basic Panel", names)

    def test_create_appointment_success_flat_fields(self):
        url = reverse('appointment-create')
        data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane.doe@example.com',
            'phone_number': '5551234567',
            'dob': '1992-05-15',
            'gender': 'female',
            'service_package': self.service_package.id,
            'appointment_date': str(datetime.date.today() + datetime.timedelta(days=1)),
            'start_time': '09:00:00',
            'location_type': 'patient home',  # mapped to 'home'
            'location': '123 Main Street',
            'medical_conditions': ['Diabetes', 'Thyroid Disorder'],
            'terms_agreement': True,
            'consent_communication': True,
            'email_result_notification': 'true',
            'sms_appointment_reminders': 'true'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.count(), 1)
        
        appointment = Appointment.objects.first()
        self.assertEqual(appointment.patient.first_name, 'Jane')
        self.assertEqual(appointment.location_type, 'home')
        self.assertEqual(appointment.medical_conditions, 'Diabetes, Thyroid')
        self.assertTrue(appointment.email_result_notification)
        self.assertTrue(appointment.sms_appointment_reminders)

    def test_create_appointment_success_nested_fields(self):
        url = reverse('appointment-create')
        data = {
            'patient': {
                'first_name': 'Alex',
                'last_name': 'Smith',
                'email': 'alex@example.com',
                'phone_number': '5557654321',
                'dob': '1988-11-20',
                'gender': 'male'
            },
            'service_package': self.service_package.id,
            'appointment_date': str(datetime.date.today() + datetime.timedelta(days=2)),
            'start_time': '10:00:00',
            'location_type': 'hospital',
            'location': 'General Hospital Room 304',
            'medical_conditions': 'High Blood Pressure',
            'terms_agreement': 'true',
            'consent_communication': 'true'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.count(), 1)
        
        appointment = Appointment.objects.first()
        self.assertEqual(appointment.patient.first_name, 'Alex')
        self.assertEqual(appointment.medical_conditions, 'High Blood Pressure')

    def test_create_appointment_missing_consent(self):
        url = reverse('appointment-create')
        data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane.doe@example.com',
            'phone_number': '5551234567',
            'dob': '1992-05-15',
            'gender': 'female',
            'service_package': self.service_package.id,
            'appointment_date': str(datetime.date.today() + datetime.timedelta(days=1)),
            'start_time': '09:00:00',
            'location_type': 'home',
            'location': '123 Main Street',
            'terms_agreement': False,  # Missing consent
            'consent_communication': True
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('terms_agreement', response.data)

    def test_create_appointment_past_date(self):
        url = reverse('appointment-create')
        data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane.doe@example.com',
            'phone_number': '5551234567',
            'dob': '1992-05-15',
            'gender': 'female',
            'service_package': self.service_package.id,
            'appointment_date': str(datetime.date.today() - datetime.timedelta(days=1)),  # Past date
            'start_time': '09:00:00',
            'location_type': 'home',
            'location': '123 Main Street',
            'terms_agreement': True,
            'consent_communication': True
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('appointment_date', response.data)

    def test_create_appointment_prescription_invalid_format(self):
        url = reverse('appointment-create')
        
        # Simulating multipart form-data upload with a text file instead of PDF/JPG
        prescription_file = SimpleUploadedFile("test.txt", b"dummy content", content_type="text/plain")
        
        data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane.doe@example.com',
            'phone_number': '5551234567',
            'dob': '1992-05-15',
            'gender': 'female',
            'service_package': self.service_package.id,
            'appointment_date': str(datetime.date.today() + datetime.timedelta(days=1)),
            'start_time': '09:00:00',
            'location_type': 'home',
            'location': '123 Main Street',
            'prescription': prescription_file,
            'terms_agreement': True,
            'consent_communication': True
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('prescription', response.data)

    def test_create_appointment_prescription_large_file(self):
        url = reverse('appointment-create')
        
        # Simulating file > 5MB (5.1MB = 5.1 * 1024 * 1024 bytes)
        large_content = b"0" * int(5.1 * 1024 * 1024)
        prescription_file = SimpleUploadedFile("large.jpg", large_content, content_type="image/jpeg")
        
        data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane.doe@example.com',
            'phone_number': '5551234567',
            'dob': '1992-05-15',
            'gender': 'female',
            'service_package': self.service_package.id,
            'appointment_date': str(datetime.date.today() + datetime.timedelta(days=1)),
            'start_time': '09:00:00',
            'location_type': 'home',
            'location': '123 Main Street',
            'prescription': prescription_file,
            'terms_agreement': True,
            'consent_communication': True
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('prescription', response.data)

    def test_phlebotomist_cannot_view_all_appointments(self):
        # Create an appointment
        patient = PatientProfile.objects.create(
            first_name="Jane", last_name="Doe", email="jane@example.com",
            phone_number="123", dob="1990-01-01", gender="female"
        )
        Appointment.objects.create(
            patient=patient, service_package=self.service_package,
            appointment_date=datetime.date.today(), start_time="09:00:00",
            location_type="home", location="123 Street"
        )
        
        # Authenticate as phlebotomist
        self.client.force_authenticate(user=self.phlebotomist_user)
        url = reverse('appointment-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see 0 since they are not assigned
        self.assertEqual(len(response.data['results']), 0)

    def test_admin_can_view_all_appointments(self):
        patient = PatientProfile.objects.create(
            first_name="Jane", last_name="Doe", email="jane@example.com",
            phone_number="123", dob="1990-01-01", gender="female"
        )
        Appointment.objects.create(
            patient=patient, service_package=self.service_package,
            appointment_date=datetime.date.today(), start_time="09:00:00",
            location_type="home", location="123 Street"
        )
        
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('appointment-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_appointment_updates_existing_patient(self):
        # Create an existing patient profile
        existing_patient = PatientProfile.objects.create(
            first_name="Original",
            last_name="Name",
            email="existing@example.com",
            phone_number="1111111111",
            dob="1990-01-01",
            gender="male"
        )
        
        url = reverse('appointment-create')
        data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'existing@example.com',
            'phone_number': '9999999999',
            'dob': '1990-01-01',
            'gender': 'female',
            'service_package': self.service_package.id,
            'appointment_date': str(datetime.date.today() + datetime.timedelta(days=1)),
            'start_time': '09:00:00',
            'location_type': 'home',
            'location': '456 Updated St',
            'terms_agreement': True,
            'consent_communication': True
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify no new PatientProfile was created (the only one is the one we set up in this test)
        self.assertEqual(PatientProfile.objects.filter(email='existing@example.com').count(), 1)
        
        # Verify the existing profile was updated
        existing_patient.refresh_from_db()
        self.assertEqual(existing_patient.first_name, 'UpdatedFirst')
        self.assertEqual(existing_patient.last_name, 'UpdatedLast')
        self.assertEqual(existing_patient.phone_number, '9999999999')
        self.assertEqual(existing_patient.gender, 'female')


from appointments.models import Wallet, WalletTransaction, PayoutRequest

class WalletAndPayoutTests(APITestCase):

    def setUp(self):
        # Create user profiles
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="password123",
            full_name="Jane Client",
            phone_number="1231231230",
            gender="female",
            dob="1992-01-01",
            role=User.CLIENT
        )
        self.phleb_user = User.objects.create_user(
            email="phleb2@example.com",
            password="password123",
            full_name="Bob Phleb",
            phone_number="1234123412",
            gender="male",
            dob="1991-01-01",
            role=User.PHLEBOTOMIST
        )
        self.admin_user = User.objects.create_user(
            email="admin2@example.com",
            password="password123",
            full_name="Admin Boss",
            phone_number="9876987698",
            gender="male",
            dob="1980-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.service_package = ServicePackage.objects.create(
            name="Deluxe Package",
            price=200.00,
            is_active=True
        )

    def test_wallet_creation_on_user_save(self):
        self.assertTrue(hasattr(self.client_user, 'wallet'))
        self.assertTrue(hasattr(self.phleb_user, 'wallet'))
        self.assertEqual(self.client_user.wallet.balance, 0)

    def test_get_wallet_balance(self):
        self.client.force_authenticate(user=self.phleb_user)
        url = reverse('wallet-balance')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['balance']), 0.0)

    def test_payout_request_success(self):
        wallet = self.phleb_user.wallet
        wallet.balance = 500.00
        wallet.save()

        self.client.force_authenticate(user=self.phleb_user)
        url = reverse('wallet-payout-request')
        data = {'amount': 200.00}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        wallet.refresh_from_db()
        self.assertEqual(float(wallet.balance), 300.0)
        self.assertEqual(PayoutRequest.objects.filter(user=self.phleb_user).count(), 1)

    def test_payout_request_insufficient_balance(self):
        self.client.force_authenticate(user=self.phleb_user)
        url = reverse('wallet-payout-request')
        data = {'amount': 200.00}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient balance", response.data['detail'])

    def test_client_invite_phlebotomist(self):
        patient = PatientProfile.objects.create(
            first_name="Jane", last_name="Doe", email="jane@example.com",
            phone_number="123", dob="1990-01-01", gender="female"
        )
        appointment = Appointment.objects.create(
            patient=patient, service_package=self.service_package,
            appointment_date=datetime.date.today(), start_time="09:00:00",
            location_type="home", location="123 Street", client=self.client_user,
            status=Appointment.CONFIRMED
        )

        self.client.force_authenticate(user=self.client_user)
        url = reverse('client-invite-phlebotomist', kwargs={'appointment_id': appointment.id})
        data = {'user_id': self.phleb_user.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        from jobs.models import Job, JobAssignment
        self.assertTrue(Job.objects.filter(appointment=appointment).exists())
        job = Job.objects.get(appointment=appointment)
        self.assertEqual(job.status, Job.APPROVED)
        self.assertTrue(JobAssignment.objects.filter(job=job, phlebotomist=self.phleb_user).exists())

    def test_admin_assign_phlebotomist(self):
        patient = PatientProfile.objects.create(
            first_name="Jane", last_name="Doe", email="jane@example.com",
            phone_number="123", dob="1990-01-01", gender="female"
        )
        appointment = Appointment.objects.create(
            patient=patient, service_package=self.service_package,
            appointment_date=datetime.date.today(), start_time="09:00:00",
            location_type="home", location="123 Street", client=self.client_user,
            status=Appointment.CONFIRMED
        )

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-assign-appointment-user', kwargs={'appointment_id': appointment.id})
        data = {'user_id': self.phleb_user.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        from jobs.models import Job, JobAssignment
        job = Job.objects.get(appointment=appointment)
        self.assertEqual(job.status, Job.IN_PROGRESS)
        assignment = JobAssignment.objects.get(job=job)
        self.assertEqual(assignment.status, JobAssignment.ACTIVE)


class PatientScreenAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.client_user = User.objects.create_user(
            email="client_patient_test@example.com",
            password="testpassword123",
            full_name="Jane Client",
            phone_number="1231231230",
            gender="female",
            dob="1992-01-01",
            role=User.CLIENT
        )
        self.phleb_user = User.objects.create_user(
            email="phleb_patient_test@example.com",
            password="testpassword123",
            full_name="Bob Phleb",
            phone_number="1234123412",
            gender="male",
            dob="1991-01-01",
            role=User.PHLEBOTOMIST
        )
        self.other_client_user = User.objects.create_user(
            email="other_client@example.com",
            password="testpassword123",
            full_name="Other Client",
            phone_number="0001112223",
            gender="female",
            dob="1990-01-01",
            role=User.CLIENT
        )
        self.admin_user = User.objects.create_user(
            email="admin_patient_test@example.com",
            password="testpassword123",
            full_name="Admin User",
            phone_number="0987654321",
            gender="female",
            dob="1990-01-01",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.service_package = ServicePackage.objects.create(
            name="Patient Test Package",
            description="Test package description",
            price=89.00,
            is_active=True
        )
        
        # Create patients
        self.patient1 = PatientProfile.objects.create(
            first_name="Fahmida",
            last_name="Tasnim",
            email="fahmida@example.com",
            phone_number="+1 555-0123",
            dob=datetime.date(1990, 6, 15),
            gender="female"
        )
        self.patient2 = PatientProfile.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="+1 555-0124",
            dob=datetime.date(1985, 10, 10),
            gender="male"
        )
        
        # Create appointments
        # Client 1 owns appointment 1
        self.appointment1 = Appointment.objects.create(
            patient=self.patient1,
            client=self.client_user,
            service_package=self.service_package,
            appointment_date=datetime.date(2024, 12, 15),
            start_time=datetime.time(10, 30),
            location_type="home",
            location="1234 Oak Street, Apt 5B, Springfield, IL 62701",
            special_requests="Patient requires fasting blood work. Last meal 12 hours ago.",
            status=Appointment.CONFIRMED
        )
        
        # Client 2 owns appointment 2
        self.appointment2 = Appointment.objects.create(
            patient=self.patient2,
            client=self.other_client_user,
            service_package=self.service_package,
            appointment_date=datetime.date(2024, 12, 16),
            start_time=datetime.time(11, 30),
            location_type="hospital",
            location="City Clinic Room 12",
            status=Appointment.CONFIRMED
        )

    def test_patient_list_for_client_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('patient-list') + f"?user_id={self.client_user.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see only patient1's appointment
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['appointment_id'], self.appointment1.id)
        self.assertEqual(results[0]['patient_name'], "Fahmida Tasnim")
        self.assertTrue(results[0]['patient_id'].startswith("SID-"))

    def test_patient_list_for_phlebotomist_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        
        # Assign phlebotomist to job for appointment2
        from jobs.models import Job, JobAssignment
        job = Job.objects.create(
            id="JB-24-999999",
            appointment=self.appointment2,
            client=self.other_client_user,
            title="Job 2",
            description="Desc 2",
            location="City Clinic",
            shift_date=datetime.date(2024, 12, 16),
            shift_start=datetime.time(11, 30),
            shift_end=datetime.time(12, 30),
            pay_rate=89.00,
            status=Job.APPROVED
        )
        JobAssignment.objects.create(
            job=job,
            phlebotomist=self.phleb_user,
            status=JobAssignment.ACTIVE
        )
        
        url = reverse('patient-list') + f"?user_id={self.phleb_user.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see patient2's appointment now
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['appointment_id'], self.appointment2.id)
        self.assertEqual(results[0]['patient_name'], "John Doe")

    def test_patient_list_unauthorized(self):
        # Non-admin user should get 403 Forbidden
        self.client.force_authenticate(user=self.client_user)
        url = reverse('patient-list') + f"?user_id={self.client_user.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_appointment_detail_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('patient-appointment-detail', kwargs={'pk': self.appointment1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        # Verify patient info
        self.assertEqual(data['patient_info']['name'], "Fahmida Tasnim")
        self.assertIn("years", data['patient_info']['age'])
        self.assertEqual(data['patient_info']['phone'], "+1 555-0123")
        self.assertEqual(data['patient_info']['date'], "Dec 15, 2024")
        self.assertEqual(data['patient_info']['time'], "10:30 AM")
        
        # Verify medical info
        self.assertEqual(data['medical_info']['special_instructions'], "Patient requires fasting blood work. Last meal 12 hours ago.")
        
        # Verify location
        self.assertEqual(data['location']['type'], "Patient's Home")
        self.assertEqual(data['location']['address'], "1234 Oak Street, Apt 5B, Springfield, IL 62701")
        
        # Verify service details
        self.assertEqual(data['service_details']['name'], "Patient Test Package")
        
        # Verify service overview
        self.assertEqual(data['service_overview']['service'], "Mobile Blood Draw")
        self.assertEqual(data['service_overview']['total_amount'], "$89.00")

    def test_patient_appointment_detail_unauthorized(self):
        # Non-admin trying to access detail should be forbidden
        self.client.force_authenticate(user=self.client_user)
        url = reverse('patient-appointment-detail', kwargs={'pk': self.appointment1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


