import json
import re
import random
import uuid
from rest_framework.response import Response
from rest_framework import status
from phlebotomy_staffing.base import NewAPIView
from authentication import models, serializers
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import AllowAny, IsAuthenticated
from authentication.tasks import send_reset_otp_email
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# Phlebotomist Registration View
class PhlebotomistRegistrationView(NewAPIView):
    serializer_class = serializers.PhlebotomistRegistrationSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request):
        """
        **Register a new Phlebotomist account**\n

        ### Request Data Format:
        This endpoint supports both JSON (`application/json`) payloads and Multipart (`multipart/form-data`) uploads. 
        Nested resources (such as availabilities, skills, and documents) can be passed as:
        1. Stringified JSON structures.
        2. Indexed fields using array bracket syntax (e.g. `availabilities[0]day` or `documents[0]document_file`).

        ### Required Fields:
        - **User Identity:**
          - `full_name` (string): Full legal name.
          - `email` (string): Unique email address.
          - `password` (string): Strong password (minimum 8 characters, at least 1 digit, 1 uppercase, 1 lowercase, and 1 special character).
          - `phone_number` (string): Primary contact phone number.
          - `gender` (string): Gender value. Choices: `male`, `female`, `other`.
          - `dob` (date): Date of birth in YYYY-MM-DD format.
        - **Professional Details:**
          - `license_number` (string): Professional licensing identifier.
          - `license_expiry_date` (date): Expiry date of the license (YYYY-MM-DD).
          - `years_of_experience` (integer): Total years of professional phlebotomy experience. Must be >= 0.
          - `specialty` (string): Medical draws specialty. Choices: `general_phlebotomy`, `pediatric_draw`, `geriatric_draw`, `mobile_phlebotomy`, `iv_insertion_or_therapy`, `capillary_puncture`, `venipuncture`.
          - `work_preference` (string): Scheduling preference. Choices: `full_time`, `part_time`, `contract`, `on_call`.
          - `service_area` (string): Primary geographical area or city of service.
        - **Nested Profiles (At least one item required in each):**
          - `availabilities` (list): Weekly working slots. Each slot requires `day`, `date`, `start_time`, `end_time`, and `is_available`.
          - `skills` (list of strings): List of specific phlebotomist drawing skills/techniques.
          - `documents` (list): Onboarding validation documents. Each item requires `document_name` and a `document_file` file upload.

        ### Optional Fields:
        - `profile_picture` (file/image): Optional profile picture file.
        - `address` (string): Optional home/work street address.

        ### Example Request:
        ```json
        {
            "full_name": "Jane Doe",
            "email": "[EMAIL_ADDRESS]",
            "password": "Password123!",
            "phone_number": "1234567890",
            "gender": "female",
            "dob": "1990-01-01",
            "license_number": "123456789",
            "license_expiry_date": "2025-12-31",
            "years_of_experience": 5,
            "specialty": "general_phlebotomy",
            "work_preference": "full_time",
            "service_area": "New York",
            "availabilities": [
                {
                    "day": "Monday",
                    "date": "2025-01-01",
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "is_available": true
                }
            ],
            "skills": [
                "venipuncture",
                "capillary_puncture",
                "pediatric_draw"
            ],
            "documents": [
                {
                    "document_name": "license",
                    "document_file": "file.pdf"
                }
            ]
        }
        ```

        ### Example Success Response:
        ```json
        {
            "message": "Phlebotomist account registered successfully. Your profile is pending admin approval. You will receive an email notification once your account is approved. You'll be able to log in after that!"
        }
        ```

        ### Responses:
        - **201 Created**: Account successfully registered. Returns a message indicating pending admin approval.
        - **400 Bad Request**: Validation failed (e.g., missing required fields, email already exists, weak password, or empty nested list values).
        """
        # Convert request.data to a plain dict to avoid QueryDict list-wrapping behavior
        data = {}
        if hasattr(request.data, 'getlist'):
            for key in request.data.keys():
                values = request.data.getlist(key)
                data[key] = values if len(values) > 1 else request.data[key]
        else:
            data = dict(request.data)
        
        # 1. Parse stringified JSON fields (like availabilities, skills, documents) if sent as strings in multipart
        for key in ['availabilities', 'skills', 'documents']:
            if key in data and isinstance(data[key], str):
                try:
                    data[key] = json.loads(data[key])
                except json.JSONDecodeError:
                    return Response(
                        {key: [f"Invalid JSON format for {key}."]},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # 2. Extract nested structures if sent using array brackets (e.g., availabilities[0]day or availabilities[0][day])
        if request.content_type and 'multipart/form-data' in request.content_type:
            parsed_arrays = {}
            pattern = re.compile(r'^(\w+)\[(\d+)\](?:\[?(\w+)\]?)?$')
            for key in request.data.keys():
                match = pattern.match(key)
                if match:
                    name, index, attr = match.groups()
                    index = int(index)
                    
                    if name not in parsed_arrays:
                        parsed_arrays[name] = []
                    while len(parsed_arrays[name]) <= index:
                        parsed_arrays[name].append({})
                    
                    val = request.data[key]
                    if attr:
                        if isinstance(parsed_arrays[name][index], dict):
                            parsed_arrays[name][index][attr] = val
                    else:
                        parsed_arrays[name][index] = val

            # Merge parsed array data back into the request data dict if they weren't passed as JSON strings
            for key, val in parsed_arrays.items():
                if key not in data or not data[key]:
                    data[key] = val

        # 3. Associate uploaded files from request.FILES with the documents list
        documents_list = data.get('documents', [])
        if isinstance(documents_list, list):
            for i in range(len(documents_list)):
                doc = documents_list[i]
                if isinstance(doc, dict):
                    # Look for document files in request.FILES matching index i
                    file_keys = [f'document_file_{i}', f'documents[{i}]document_file', f'documents[{i}][document_file]']
                    for fk in file_keys:
                        if fk in request.FILES:
                            doc['document_file'] = request.FILES[fk]
                            break

        # 4. Associate profile_picture from request.FILES if uploaded
        if 'profile_picture' in request.FILES:
            data['profile_picture'] = request.FILES['profile_picture']

        # 5. Run standard serializer validation and save
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # 6. Return registration success message indicating admin review
        return Response(
            {
                "message": "Phlebotomist account registered successfully. Your profile is pending admin approval. You will receive an email notification once your account is approved. You'll be able to log in after that!"
            },
            status=status.HTTP_201_CREATED,
        )

# Client Registration View
class ClientRegistrationView(NewAPIView):
    serializer_class = serializers.ClientRegistrationSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request):
        """
        **Register a new Client account**\n

        ### Request Data Format:
        This endpoint supports both JSON (`application/json`) payloads and Multipart (`multipart/form-data`) uploads.
        Nested resources (such as availabilities and documents) can be passed as:
        1. Stringified JSON structures.
        2. Indexed fields using array bracket syntax (e.g. `availabilities[0]day` or `documents[0]document_file`).

        ### Required Fields:
        - **User Identity:**
          - `full_name` (string): Full legal name of the account holder.
          - `email` (string): Unique email address.
          - `password` (string): Strong password (minimum 8 characters, at least 1 digit, 1 uppercase, 1 lowercase, and 1 special character).
          - `phone_number` (string): Primary contact phone number.
          - `gender` (string): Gender value. Choices: `male`, `female`.
          - `dob` (date): Date of birth in YYYY-MM-DD format.
        - **Business Details:**
          - `business_name` (string): Registered name of the business or organisation.
          - `business_type` (string): Type of business. Choices: `healthcare`, `individual`.
          - `business_address_street` (string): Street line of the business address.
          - `business_address_city` (string): City of the business address.
          - `business_address_state` (string): State of the business address.
          - `business_address_zip` (string): ZIP / postal code of the business address.
          - `contact_person_name` (string): Name of the primary point of contact.
          - `business_phone` (string): Business phone number.
          - `business_license_number` (string): Official business license identifier.
          - `business_description` (string): Brief description of the business and its services.
          - `hourly_pay_rate` (decimal): Offered hourly compensation rate (e.g. `25.00`).
          - `preferred_job_type` (string): Type of phlebotomy work required. Choices: `in_clinic_phlebotomy`, `mobile_blood_draw`, `laboratory_testing`.
          - `work_preference` (string): Scheduling preference. Choices: `full_time`, `part_time`.
          - `signature` (file/image): Required signature image of the authorised contact person.
        - **Nested Profiles (At least one item required in each):**
          - `availabilities` (list): Weekly schedule slots when phlebotomists are needed. Each slot requires `day`, `date`, `start_time`, `end_time`, and `is_available`.
          - `documents` (list): Onboarding verification documents. Each item requires `document_name` and a `document_file` file upload.

        ### Optional Fields:
        - `profile_picture` (file/image): Optional profile picture for the account holder.

        ### Example Request:
        ```json
        {
            "full_name": "John Smith",
            "email": "[EMAIL_ADDRESS]",
            "password": "Password123!",
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
            "signature": "signature.png",
            "availabilities": [
                {
                    "day": "Monday",
                    "date": "2025-01-06",
                    "start_time": "08:00",
                    "end_time": "16:00",
                    "is_available": true
                }
            ],
            "documents": [
                {
                    "document_name": "business_license",
                    "document_file": "license.pdf"
                }
            ]
        }
        ```

        ### Example Success Response:
        ```json
        {
            "message": "Client account registered successfully. Your profile is pending admin approval. You will receive an email notification once your account is approved. You'll be able to log in after that!"
        }
        ```

        ### Responses:
        - **201 Created**: Account successfully registered. Returns a message indicating pending admin approval.
        - **400 Bad Request**: Validation failed (e.g., missing required fields, email already exists, weak password, or empty nested list values).
        """
        # Convert request.data to a plain dict to avoid QueryDict list-wrapping behavior
        data = {}
        if hasattr(request.data, 'getlist'):
            for key in request.data.keys():
                values = request.data.getlist(key)
                data[key] = values if len(values) > 1 else request.data[key]
        else:
            data = dict(request.data)

        # 1. Parse stringified JSON fields (like availabilities, documents) if sent as strings in multipart
        for key in ['availabilities', 'documents']:
            if key in data and isinstance(data[key], str):
                try:
                    data[key] = json.loads(data[key])
                except json.JSONDecodeError:
                    return Response(
                        {key: [f"Invalid JSON format for {key}."]},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # 2. Extract nested structures if sent using array brackets (e.g., availabilities[0]day or availabilities[0][day])
        if request.content_type and 'multipart/form-data' in request.content_type:
            parsed_arrays = {}
            pattern = re.compile(r'^(\w+)\[(\d+)\](?:\[?(\w+)\]?)?$')
            for key in request.data.keys():
                if match := pattern.match(key):
                    name, index, attr = match.groups()
                    index = int(index)

                    if name not in parsed_arrays:
                        parsed_arrays[name] = []
                    while len(parsed_arrays[name]) <= index:
                        parsed_arrays[name].append({})

                    val = request.data[key]
                    if attr:
                        if isinstance(parsed_arrays[name][index], dict):
                            parsed_arrays[name][index][attr] = val
                    else:
                        parsed_arrays[name][index] = val

            # Merge parsed array data back into the request data dict if they weren't passed as JSON strings
            for key, val in parsed_arrays.items():
                if key not in data or not data[key]:
                    data[key] = val

        # 3. Associate uploaded files from request.FILES with the documents list
        documents_list = data.get('documents', [])
        if isinstance(documents_list, list):
            for i in range(len(documents_list)):
                doc = documents_list[i]
                if isinstance(doc, dict):
                    # Look for document files in request.FILES matching index i
                    file_keys = [f'document_file_{i}', f'documents[{i}]document_file', f'documents[{i}][document_file]']
                    for fk in file_keys:
                        if fk in request.FILES:
                            doc['document_file'] = request.FILES[fk]
                            break

        # 4. Associate profile_picture from request.FILES if uploaded
        if 'profile_picture' in request.FILES:
            data['profile_picture'] = request.FILES['profile_picture']

        # 5. Associate signature from request.FILES
        if 'signature' in request.FILES:
            data['signature'] = request.FILES['signature']

        # 6. Run standard serializer validation and save
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # 7. Return registration success message indicating admin review
        return Response(
            {
                "message": "Client account registered successfully. Your profile is pending admin approval. You will receive an email notification once your account is approved. You'll be able to log in after that!"
            },
            status=status.HTTP_201_CREATED,
        )

class RequestForgetPasswordAPIView(NewAPIView):
    serializer_class = serializers.EmailSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request):
        """
        **Request Forget Password Endpoint - Public**\n
        Request a password reset OTP to be sent to the user's email address.
        
        **Request Body:**
        - **email**: The email address of the user (string, required).

        **Response:**
        - **success**: A boolean indicating whether the OTP was sent successfully.
        - **message**: A message providing additional information about the OTP request result.
        """
        data = request.data
        email = data.get('email')
        if not email:
            return Response({"success": False, "message": "Email field is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.otp_created_at = timezone.now()
            user.forgot_password_token = str(uuid.uuid4())
            user.save()
            send_reset_otp_email.delay(email, otp)
            return Response({"success": True, "message": "A password reset OTP has been sent to your email."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"success": False, "message": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

class VerifyForgetPasswordOTPAPIView(NewAPIView):
    serializer_class = serializers.EmailOTPSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request):
        """
        **Verify Forget Password OTP Endpoint - Public**\n
        Verify the OTP sent to the user's email for password reset.
        
        **Request Body:**
        - **email**: The email address of the user (string, required).
        - **otp**: The OTP sent to the user's email (string, required).

        **Response:**
        - **success**: A boolean indicating whether the OTP was verified successfully.
        - **message**: A message providing additional information about the OTP verification result.
        - **email**: The email address of the user (string, returned only if OTP is verified successfully).
        - **forgot_password_token**: A token that can be used to reset the password (string, returned only if OTP is verified successfully).
        """
        data = request.data
        email = data.get('email')
        otp = data.get('otp')
        if not email or not otp:
            return Response({"success": False, "message": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
            if user.forgot_password_token is None:
                return Response({"success": False, "message": "No password reset request found for this email."}, status=status.HTTP_400_BAD_REQUEST)
            if user.otp_created_at and timezone.now() - user.otp_created_at > timezone.timedelta(minutes=15):
                return Response({"success": False, "message": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)
            if user.otp != otp:
                return Response({"success": False, "message": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
            user.otp = None
            user.otp_created_at = None
            user.save()
            return Response({"success": True, "message": "OTP verified successfully.", "email": user.email, "forgot_password_token": user.forgot_password_token}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"success": False, "message": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

class ResetPasswordAPIView(NewAPIView):
    serializer_class = serializers.ResetPasswordSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request):
        """
        **Reset Password Endpoint - Public**\n
        Reset the password for a user using the provided email, OTP, and new password.
        
        **Request Body:**
        - **email**: The email address of the user (string, required).
        - **otp**: The OTP sent to the user's email (string, required).
        - **new_password**: The new password for the user (string, required).

        **Response:**
        - **success**: A boolean indicating whether the password was reset successfully.
        - **message**: A message providing additional information about the password reset result.
        """
        data = request.data
        email = data.get('email')
        forgot_password_token = data.get('forgot_password_token')
        new_password = data.get('new_password')
        if not email or not forgot_password_token or not new_password:
            return Response({"success": False, "message": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
            if user.forgot_password_token != forgot_password_token:
                return Response({"success": False, "message": "Invalid forgot password token."}, status=status.HTTP_400_BAD_REQUEST)
            if user.otp:
                return Response({"success": False, "message": "OTP has not been verified yet."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                validate_password(new_password)
            except ValidationError as e:
                return Response({"success": False, "message": e.messages.pop()}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)
            user.forgot_password_token = None
            user.save()
            return Response({"success": True, "message": "Password reset successfully."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"success": False, "message": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"success": False, "message": e.messages.pop()}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AccountDeleteAPIView(NewAPIView):
    serializer_class = serializers.EmptySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['delete']
    
    @swagger_auto_schema(tags=['Authentication'])
    def delete(self, request):
        """
        **Delete Account Endpoint - Authenticated**\n
        Delete the authenticated user's account.
        
        **Response:**
        - **success**: A boolean indicating whether the account was deleted successfully.
        - **message**: A message providing additional information about the account deletion result.
        """
        try:
            if request.user.is_superuser:
                return Response({"success": False, "message": "Superuser accounts cannot be deleted."}, status=status.HTTP_400_BAD_REQUEST)
            request.user.delete()
            return Response({"success": True, "message": "Account deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChangePasswordView(NewAPIView):
    serializer_class = serializers.ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request):
        """
        **Change Password Endpoint - Authentication Required**\n
        Allow authenticated users to change their password.
        
        **Request Body:**
        - **old_password**: The current password of the user (string, required).
        - **new_password**: The new password for the user (string, required).

        **Response:**
        - **success**: A boolean indicating whether the password was changed successfully.
        - **message**: A message providing additional information about the password change result.
        """
        data = request.data
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        if not old_password or not new_password:
            return Response({"success": False, "message": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        if not user.check_password(old_password):
            return Response({"success": False, "message": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(new_password)
        except ValidationError as e:
            return Response({"success": False, "message": e.messages.pop()}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({"success": True, "message": "Password changed successfully."}, status=status.HTTP_200_OK)

class UserLoginView(NewAPIView):
    serializer_class = serializers.LoginSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request):
        """
        **Universal Login Endpoint - Public**\n
        Authenticate a user and return access and refresh tokens.
        
        **Request Body:**
        - **email**: The email address of the user (string, required).
        - **password**: The password of the user (string, required).
        - **role**: The role of the user (string, required) options: `admin`, `phlebotomist`, `client`.

        **Example Response:**
        ```
        {
            "success": true,
            "message": "Account activated successfully.",
            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "user_id": 3,
            "user_full_name": "Md. Fahad Monshi",
            "user_email": "fahad4bangladesh@gmail.com",
            "user_phone_number": null,
            "user_profile_picture": null,
            "is_approved": true,
            "role": "phlebotomist"
        }
        ```
        """
        if not request.data.get('email') or not request.data.get('password') or not request.data.get('role'):
            return Response({"success": False, "message": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            role = serializer.validated_data['role']
            try:
                user = User.objects.get(email=email, role=role)
                if not user:
                    return Response({"success": False, "message": "Invalid credentials."}, status=status.HTTP_404_NOT_FOUND)
                if not user.check_password(password):
                    return Response({"success": False, "message": "Invalid credentials."}, status=status.HTTP_404_NOT_FOUND)
                if not user.is_active:
                    return Response({"success": False, "message": "Account is not active. Please activate your account first."}, status=status.HTTP_403_FORBIDDEN)
                
                if user.role == 'phlebotomist' and hasattr(user, 'phlebotomist_profile') and not user.phlebotomist_profile.approved:
                    return Response({"success": False, "message": "Your account is not approved yet."}, status=status.HTTP_404_NOT_FOUND)
                
                if user.role == 'client' and hasattr(user, 'client_profile') and not user.client_profile.is_approved:
                    return Response({"success": False, "message": "Your account is not approved yet."}, status=status.HTTP_404_NOT_FOUND)
                
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                return Response({
                    "success": True, 
                    "message": "Login successful.", 
                    "access": access_token, 
                    "refresh": refresh_token,
                    "user_id": user.id,
                    "user_full_name": user.full_name,
                    "user_email": user.email,
                    "user_phone_number": user.phone_number,
                    "user_profile_picture": request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
                    "is_approved": user.phlebotomist_profile.approved if user.role == 'phlebotomist' else (user.client_profile.is_approved if user.role == 'client' else None),
                    "role": user.role,
                    }, status=status.HTTP_200_OK)        
            except User.DoesNotExist:
                return Response({"success": False, "message": "Invalid credentials."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": False, "message": "Invalid input data."}, status=status.HTTP_400_BAD_REQUEST)



