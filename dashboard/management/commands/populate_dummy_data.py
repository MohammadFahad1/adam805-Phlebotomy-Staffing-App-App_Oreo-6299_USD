import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.base import ContentFile
from authentication.models import (
    Client, ClientDocument, ClientWeeklySchedule,
    Phlebotomist, PhlebotomistAvailability, Phlebotomist_skill, Phlebotomist_document
)
from appointments.models import (
    ServicePackage, ServicePackageFeature, PatientProfile, Appointment, Payment,
    PlatformSetting, Wallet, WalletTransaction, PayoutRequest
)
from jobs.models import Job, JobApplication, JobAssignment, JobTemplate
from communication.models import Message, Review, Notification, Report

User = get_user_model()

class Command(BaseCommand):
    help = "Populates the database with comprehensive dummy data for testing and integration."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write("Clearing existing data...")
            Report.objects.all().delete()
            Notification.objects.all().delete()
            Review.objects.all().delete()
            Message.objects.all().delete()
            JobAssignment.objects.all().delete()
            JobApplication.objects.all().delete()
            JobTemplate.objects.all().delete()
            Job.objects.all().delete()
            PayoutRequest.objects.all().delete()
            WalletTransaction.objects.all().delete()
            Wallet.objects.all().delete()
            Payment.objects.all().delete()
            Appointment.objects.all().delete()
            PatientProfile.objects.all().delete()
            ServicePackageFeature.objects.all().delete()
            ServicePackage.objects.all().delete()
            ClientWeeklySchedule.objects.all().delete()
            ClientDocument.objects.all().delete()
            Client.objects.all().delete()
            Phlebotomist_document.objects.all().delete()
            Phlebotomist_skill.objects.all().delete()
            PhlebotomistAvailability.objects.all().delete()
            Phlebotomist.objects.all().delete()
            User.objects.all().delete()
            PlatformSetting.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing data cleared."))

        self.stdout.write("Populating dummy data...")

        # 1. Platform Settings
        setting, _ = PlatformSetting.objects.get_or_create(key='platform_fee_percentage', defaults={'value': 15.00})

        # 2. Create Users
        admin_user, _ = User.objects.get_or_create(
            email="admin@example.com",
            defaults={
                "full_name": "System Administrator",
                "phone_number": "1112223333",
                "gender": "male",
                "dob": "1985-01-01",
                "role": User.ADMIN,
                "is_staff": True,
                "is_superuser": True
            }
        )
        if _:
            admin_user.set_password("AdminSecure123!")
            admin_user.save()

        # Clients
        client1, _ = User.objects.get_or_create(
            email="client@example.com",
            defaults={
                "full_name": "Smith Healthcare LLC",
                "phone_number": "2223334444",
                "gender": "male",
                "dob": "1980-05-10",
                "role": User.CLIENT
            }
        )
        if _:
            client1.set_password("SecurePassword123!")
            client1.save()

        client2, _ = User.objects.get_or_create(
            email="approved_client@example.com",
            defaults={
                "full_name": "Sarah Connor",
                "phone_number": "3334445555",
                "gender": "female",
                "dob": "1982-11-20",
                "role": User.CLIENT
            }
        )
        if _:
            client2.set_password("SecurePassword123!")
            client2.save()

        # Phlebotomists
        phleb1, _ = User.objects.get_or_create(
            email="phleb@example.com",
            defaults={
                "full_name": "John Phlebotomist",
                "phone_number": "4445556666",
                "gender": "male",
                "dob": "1990-03-15",
                "role": User.PHLEBOTOMIST
            }
        )
        if _:
            phleb1.set_password("SecurePassword123!")
            phleb1.save()

        phleb2, _ = User.objects.get_or_create(
            email="approved_phleb@example.com",
            defaults={
                "full_name": "FA Kabita",
                "phone_number": "5556667777",
                "gender": "female",
                "dob": "1992-07-25",
                "role": User.PHLEBOTOMIST
            }
        )
        if _:
            phleb2.set_password("SecurePassword123!")
            phleb2.save()

        phleb3, _ = User.objects.get_or_create(
            email="phleb_alt@example.com",
            defaults={
                "full_name": "Jane Miller",
                "phone_number": "6667778888",
                "gender": "female",
                "dob": "1988-09-05",
                "role": User.PHLEBOTOMIST
            }
        )
        if _:
            phleb3.set_password("SecurePassword123!")
            phleb3.save()

        # Dummy users specifically for testing the chat UI mockups
        mubin_user, _ = User.objects.get_or_create(
            email="mubin@example.com",
            defaults={
                "full_name": "Al Mubin",
                "phone_number": "1234567890",
                "gender": "male",
                "dob": "1994-04-12",
                "role": User.CLIENT
            }
        )
        if _:
            mubin_user.set_password("SecurePassword123!")
            mubin_user.save()

        arafat_user, _ = User.objects.get_or_create(
            email="arafat@example.com",
            defaults={
                "full_name": "Al Arafat",
                "phone_number": "2345678901",
                "gender": "male",
                "dob": "1993-08-20",
                "role": User.PHLEBOTOMIST
            }
        )
        if _:
            arafat_user.set_password("SecurePassword123!")
            arafat_user.save()

        shoiab_user, _ = User.objects.get_or_create(
            email="shoiab@example.com",
            defaults={
                "full_name": "Shoiab Akther",
                "phone_number": "3456789012",
                "gender": "male",
                "dob": "1995-10-15",
                "role": User.PHLEBOTOMIST
            }
        )
        if _:
            shoiab_user.set_password("SecurePassword123!")
            shoiab_user.save()

        shamin_user, _ = User.objects.get_or_create(
            email="shamin@example.com",
            defaults={
                "full_name": "Md. Shamin",
                "phone_number": "4567890123",
                "gender": "male",
                "dob": "1991-12-05",
                "role": User.PHLEBOTOMIST
            }
        )
        if _:
            shamin_user.set_password("SecurePassword123!")
            shamin_user.save()

        fahmida_user, _ = User.objects.get_or_create(
            email="fahmida@example.com",
            defaults={
                "full_name": "Fahmida Tasnim",
                "phone_number": "5678901234",
                "gender": "female",
                "dob": "1996-01-22",
                "role": User.PHLEBOTOMIST
            }
        )
        if _:
            fahmida_user.set_password("SecurePassword123!")
            fahmida_user.save()


        # 3. Client Profiles
        c_profile1, _ = Client.objects.get_or_create(
            client=client1,
            defaults={
                "business_name": "Smith Clinic Group",
                "business_type": Client.HEALTHCARE,
                "business_address_street": "100 Broadway St",
                "business_address_city": "New York",
                "business_address_state": "NY",
                "business_address_zip": "10001",
                "contact_person_name": "John Smith",
                "business_phone": "2125550100",
                "business_license_number": "LIC-CL-11111",
                "business_description": "We specialize in outpatient diagnostic collection.",
                "hourly_pay_rate": 35.00,
                "preferred_job_type": Client.IN_CLINIC_PHLEBOTOMY,
                "work_preference": Client.FULL_TIME,
                "no_of_employees": 25,
                "is_approved": True
            }
        )
        c_profile2, _ = Client.objects.get_or_create(
            client=client2,
            defaults={
                "business_name": "Cyberdyne Care",
                "business_type": Client.HEALTHCARE,
                "business_address_street": "456 Tech Way",
                "business_address_city": "Dallas",
                "business_address_state": "TX",
                "business_address_zip": "75201",
                "contact_person_name": "Sarah Connor",
                "business_phone": "2145550200",
                "business_license_number": "LIC-CL-22222",
                "business_description": "Leading developer of mobile health diagnostics.",
                "hourly_pay_rate": 40.00,
                "preferred_job_type": Client.MOBILE_BLOOD_DRAW,
                "work_preference": Client.PART_TIME,
                "no_of_employees": 12,
                "is_approved": True
            }
        )

        # Client Documents & Weekly Schedule
        for profile in [c_profile1, c_profile2]:
            ClientDocument.objects.get_or_create(
                client=profile,
                document_name=ClientDocument.LICENSE,
                defaults={
                    "document_file": ContentFile(b"dummy_license_content", name="client_license.pdf"),
                    "approved": True
                }
            )
            # Create a 7-day schedule starting today
            today = datetime.date.today()
            for i in range(7):
                date_i = today + datetime.timedelta(days=i)
                day_name = date_i.strftime("%A")
                ClientWeeklySchedule.objects.get_or_create(
                    client=profile,
                    date=date_i,
                    start_time=datetime.time(9, 0),
                    end_time=datetime.time(17, 0),
                    defaults={"day": day_name, "is_available": True}
                )

        # 4. Phlebotomist Profiles
        p_profile1, _ = Phlebotomist.objects.get_or_create(
            user=phleb1,
            defaults={
                "license_number": "PHL-LIC-1111",
                "license_expiry_date": today + datetime.timedelta(days=365),
                "years_of_experience": 4,
                "specialty": Phlebotomist.GENERAL_PHLEBOTOMY,
                "work_preference": Phlebotomist.FULL_TIME,
                "service_area": "New York",
                "address": "123 Phleb Ln, NY",
                "approved": True
            }
        )
        p_profile2, _ = Phlebotomist.objects.get_or_create(
            user=phleb2,
            defaults={
                "license_number": "PHL-LIC-2222",
                "license_expiry_date": today + datetime.timedelta(days=730),
                "years_of_experience": 6,
                "specialty": Phlebotomist.IV_INSERTION_OR_THERAPY,
                "work_preference": Phlebotomist.FULL_TIME,
                "service_area": "Dallas",
                "address": "456 Kabita Way, Dallas",
                "approved": True
            }
        )
        p_profile3, _ = Phlebotomist.objects.get_or_create(
            user=phleb3,
            defaults={
                "license_number": "PHL-LIC-3333",
                "license_expiry_date": today + datetime.timedelta(days=180),
                "years_of_experience": 8,
                "specialty": Phlebotomist.MEDICAL_NURSE,
                "work_preference": Phlebotomist.PART_TIME,
                "service_area": "Dallas",
                "address": "789 Jane Rd, Dallas",
                "approved": True
            }
        )

        # Phlebotomist skills, documents & availability
        for profile in [p_profile1, p_profile2, p_profile3]:
            Phlebotomist_skill.objects.get_or_create(phlebotomist=profile, skill_name="Venipuncture")
            Phlebotomist_skill.objects.get_or_create(phlebotomist=profile, skill_name="Pediatric Collection")
            Phlebotomist_document.objects.get_or_create(
                phlebotomist=profile,
                document_name=Phlebotomist_document.LICENSE,
                approved=True,
                defaults={"document_file": ContentFile(b"dummy_license", name="phleb_license.pdf")}
            )
            # Create a 7-day availability starting today
            today = datetime.date.today()
            for i in range(7):
                date_i = today + datetime.timedelta(days=i)
                day_name = date_i.strftime("%A")
                PhlebotomistAvailability.objects.get_or_create(
                    phlebotomist=profile,
                    date=date_i,
                    start_time=datetime.time(9, 0),
                    end_time=datetime.time(17, 0),
                    defaults={"day": day_name, "is_available": True}
                )

        # 5. Service Packages & Features
        pkg1, _ = ServicePackage.objects.get_or_create(
            name="General Blood Test",
            defaults={"description": "Routine hematology profile including CBC and metabolic panel.", "price": 120.00, "is_active": True}
        )
        pkg2, _ = ServicePackage.objects.get_or_create(
            name="COVID-19 Swab & PCR",
            defaults={"description": "Rapid PCR testing with same-day digital certificate.", "price": 80.00, "is_active": True}
        )
        pkg3, _ = ServicePackage.objects.get_or_create(
            name="Geriatric Blood Draw",
            defaults={"description": "Specialized, gentle collection designed for elderly patients.", "price": 150.00, "is_active": True}
        )

        for pkg in [pkg1, pkg2, pkg3]:
            ServicePackageFeature.objects.get_or_create(service_package=pkg, name="Certified Mobile Phlebotomist")
            ServicePackageFeature.objects.get_or_create(service_package=pkg, name="Fast digital lab reports")

        # 6. Patient Profiles
        patient1, _ = PatientProfile.objects.get_or_create(
            email="bruce@waynecorp.com",
            defaults={
                "first_name": "Bruce",
                "last_name": "Wayne",
                "phone_number": "9998887777",
                "dob": "1980-02-19",
                "gender": "male"
            }
        )
        patient2, _ = PatientProfile.objects.get_or_create(
            email="clark@dailyplanet.com",
            defaults={
                "first_name": "Clark",
                "last_name": "Kent",
                "phone_number": "8887776666",
                "dob": "1985-06-18",
                "gender": "male"
            }
        )

        # 7. Appointments
        apt1, _ = Appointment.objects.get_or_create(
            patient=patient1,
            client=client2,
            service_package=pkg1,
            appointment_date=today + datetime.timedelta(days=1),
            start_time=datetime.time(10, 0),
            defaults={
                "end_time": datetime.time(11, 0),
                "location_type": "home",
                "location": "1007 Mountain Drive, Gotham",
                "medical_conditions": "No Medical Conditions",
                "status": Appointment.PENDING
            }
        )
        apt2, _ = Appointment.objects.get_or_create(
            patient=patient2,
            client=client2,
            service_package=pkg3,
            appointment_date=today - datetime.timedelta(days=2),
            start_time=datetime.time(14, 0),
            defaults={
                "end_time": datetime.time(15, 0),
                "location_type": "hospital",
                "location": "Metropolis General Hospital, Room 303",
                "medical_conditions": "Thyroid",
                "status": Appointment.COMPLETED
            }
        )

        # 8. Jobs
        job1, _ = Job.objects.get_or_create(
            title="Blood Draw Station",
            client=client2,
            shift_date=today + datetime.timedelta(days=2),
            defaults={
                "appointment": apt1,
                "description": "Perform venipuncture and capillary punctures. Ensure proper specimen handling and labeling. Maintain a clean and sterile work environment.",
                "location": "456 Tech Way, Dallas",
                "city": "Dallas",
                "shift_duration": 4,
                "shift_start": datetime.time(9, 0),
                "shift_end": datetime.time(13, 0),
                "pay_type": Job.HOURLY,
                "pay_rate": 25.00,
                "professional_type": Job.CERTIFIED_PHLEBOTOMIST,
                "job_type": Job.FULL_DAY,
                "status": Job.OPEN
            }
        )
        job2, _ = Job.objects.get_or_create(
            title="Mobile Pediatric Collection",
            client=client2,
            shift_date=today - datetime.timedelta(days=2),
            defaults={
                "appointment": apt2,
                "description": "Gentle blood draw for school children. Requires friendly approach and expertise.",
                "location": "Metropolis School District",
                "city": "Metropolis",
                "shift_duration": 6,
                "shift_start": datetime.time(8, 0),
                "shift_end": datetime.time(14, 0),
                "pay_type": Job.FLAT_RATE,
                "pay_rate": 180.00,
                "professional_type": Job.REGISTERED_NURSE,
                "job_type": Job.PART_TIME,
                "status": Job.COMPLETED
            }
        )

        # Job Templates
        JobTemplate.objects.get_or_create(
            title="Standard Clinic Shift",
            defaults={
                "description": "Routine blood draws at primary care clinic.",
                "location": "Clinic Room A",
                "city": "New York",
                "shift_duration": 8,
                "shift_date": today + datetime.timedelta(days=10),
                "shift_start": datetime.time(8, 0),
                "shift_end": datetime.time(16, 0),
                "pay_type": JobTemplate.HOURLY,
                "pay_rate": 30.00,
                "professional_type": JobTemplate.CERTIFIED_PHLEBOTOMIST,
                "job_type": JobTemplate.FULL_DAY
            }
        )

        # 9. Job Applications & Assignments
        JobApplication.objects.get_or_create(job=job1, phlebotomist=phleb2, defaults={"status": JobApplication.PENDING})
        JobApplication.objects.get_or_create(job=job1, phlebotomist=phleb3, defaults={"status": JobApplication.PENDING})

        assign1, _ = JobAssignment.objects.get_or_create(
            job=job1,
            defaults={
                "phlebotomist": phleb2,
                "client": client2,
                "status": JobAssignment.ACTIVE,
                "signed_by_phlebotomist": True,
                "signed_by_client": True
            }
        )
        assign2, _ = JobAssignment.objects.get_or_create(
            job=job2,
            defaults={
                "phlebotomist": phleb2,
                "client": client2,
                "status": JobAssignment.COMPLETED,
                "signed_by_phlebotomist": True,
                "signed_by_client": True
            }
        )

        # 10. Payments
        pmt1, _ = Payment.objects.get_or_create(
            appointment=apt1,
            defaults={
                "amount": pkg1.price,
                "payment_status": Payment.PENDING,
                "stripe_payment_id": "ch_mock_12345"
            }
        )
        pmt2, _ = Payment.objects.get_or_create(
            appointment=apt2,
            defaults={
                "amount": pkg3.price,
                "payment_status": Payment.PAID,
                "stripe_payment_id": "ch_mock_67890"
            }
        )
        pmt_job2, _ = Payment.objects.get_or_create(
            job=job2,
            defaults={
                "amount": job2.pay_rate,
                "payment_status": Payment.PAID,
                "stripe_payment_id": "ch_mock_job_999"
            }
        )

        # 11. Wallet & Transactions
        wallet_phleb2 = phleb2.wallet
        wallet_phleb2.balance = 500.00
        wallet_phleb2.total_earned = 1000.00
        wallet_phleb2.total_platform_fees = 150.00
        wallet_phleb2.save()

        WalletTransaction.objects.get_or_create(
            wallet=wallet_phleb2,
            transaction_type=WalletTransaction.CREDIT,
            amount=153.00,
            defaults={
                "platform_fee": 27.00,
                "description": f"Earnings for completing job {job2.id}",
                "reference_job": job2,
                "reference_payment": pmt_job2
            }
        )

        PayoutRequest.objects.get_or_create(
            user=phleb2,
            amount=100.00,
            defaults={
                "status": PayoutRequest.PENDING
            }
        )

        # 12. Messages
        Message.objects.get_or_create(
            sender=client2,
            receiver=phleb2,
            job=job1,
            defaults={"message_text": "Hello, thank you for accepting the job! See you on Tuesday."}
        )
        Message.objects.get_or_create(
            sender=phleb2,
            receiver=client2,
            job=job1,
            defaults={"message_text": "Hi Sarah! Yes, I will be there on time. Thanks!"}
        )

        # Seed realistic chat history for the testing phlebotomists
        for p in [phleb1, phleb2]:
            # With Al Mubin
            Message.objects.get_or_create(
                sender=mubin_user,
                receiver=p,
                message_text="Hi there! I wanted to confirm my appointment details for tomorrow.",
                defaults={"is_read": True, "is_seen": True}
            )
            Message.objects.get_or_create(
                sender=p,
                receiver=mubin_user,
                message_text="Hello John! Yes, your appointment is confirmed for tomorrow at 2:00 PM. Please arrive 15 minutes early.",
                defaults={"is_read": True, "is_seen": True}
            )
            Message.objects.get_or_create(
                sender=mubin_user,
                receiver=p,
                message_text="Perfect! Here's my location for reference.",
                defaults={"is_read": True, "is_seen": True}
            )
            Message.objects.get_or_create(
                sender=p,
                receiver=mubin_user,
                message_text="Great! I can see the building clearly. I'll be there on time.",
                defaults={"is_read": True, "is_seen": True}
            )
            Message.objects.get_or_create(
                sender=p,
                receiver=mubin_user,
                message_text="Here are the contract details we discussed.",
                defaults={"is_read": True, "is_seen": True}
            )

            # With Admin
            Message.objects.get_or_create(
                sender=admin_user,
                receiver=p,
                message_text="Perfect! Here's my location...",
                defaults={"is_read": False, "is_seen": False}
            )

            # With Al Arafat
            Message.objects.get_or_create(
                sender=arafat_user,
                receiver=p,
                message_text="Hi there! I wanted to confirm...",
                defaults={"is_read": False, "is_seen": False}
            )

            # With Shoiab Akther
            Message.objects.get_or_create(
                sender=p,
                receiver=shoiab_user,
                message_text="Yes, of course come...",
                defaults={"is_read": True, "is_seen": True}
            )

            # With Md. Shamin
            Message.objects.get_or_create(
                sender=shamin_user,
                receiver=p,
                message_text="Hi there! I wanted to ...",
                defaults={"is_read": True, "is_seen": True}
            )

            # With Fahmida Tasnim
            Message.objects.get_or_create(
                sender=fahmida_user,
                receiver=p,
                message_text="Ok,good boy !",
                defaults={"is_read": True, "is_seen": True}
            )


        # 13. Reviews
        Review.objects.get_or_create(
            job=job2,
            reviewer=client2,
            reviewed=phleb2,
            defaults={"rating": 5, "comment": "Excellent pediatric blood draw. FA Kabita was very friendly with children."}
        )

        # 14. Notifications
        Notification.objects.get_or_create(
            user=client2,
            title="New Application",
            message="Jane Miller has applied to your job posting.",
            defaults={"type": "application_update", "is_read": False}
        )
        Notification.objects.get_or_create(
            user=phleb2,
            title="Payment Received",
            message="Your payment for Blood Collection Job is processed.",
            defaults={"type": "payment", "is_read": True}
        )

        # 15. Reports
        Report.objects.get_or_create(
            reporter=client2,
            reported_user=phleb3,
            job=job1,
            defaults={
                "reason": Report.SPAM,
                "additional_details": "Sent multiple irrelevant messages.",
                "status": Report.PENDING
            }
        )

        self.stdout.write(self.style.SUCCESS("Dummy data populated successfully!"))
        self.stdout.write("\n" + "="*50)
        self.stdout.write("          DUMMY USER CREDENTIALS FOR TESTING")
        self.stdout.write("="*50)
        self.stdout.write("ADMIN:")
        self.stdout.write("  Email:    admin@example.com")
        self.stdout.write("  Password: AdminSecure123!")
        self.stdout.write("-"*50)
        self.stdout.write("CLIENTS:")
        self.stdout.write("  Email:    client@example.com")
        self.stdout.write("  Password: SecurePassword123!")
        self.stdout.write("  --")
        self.stdout.write("  Email:    approved_client@example.com")
        self.stdout.write("  Password: SecurePassword123!")
        self.stdout.write("-"*50)
        self.stdout.write("PHLEBOTOMISTS:")
        self.stdout.write("  Email:    phleb@example.com")
        self.stdout.write("  Password: SecurePassword123!")
        self.stdout.write("  --")
        self.stdout.write("  Email:    approved_phleb@example.com")
        self.stdout.write("  Password: SecurePassword123!")
        self.stdout.write("  --")
        self.stdout.write("  Email:    phleb_alt@example.com")
        self.stdout.write("  Password: SecurePassword123!")
        self.stdout.write("="*50 + "\n")
