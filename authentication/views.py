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
                
                if user.role == 'phlebotomist' and hasattr(user, 'phlebotomist_profile') and user.phlebotomist_profile.approved == None:
                    return Response({"success": False, "message": "Your account is not approved yet."}, status=status.HTTP_404_NOT_FOUND)
                
                if user.role == 'phlebotomist' and hasattr(user, 'phlebotomist_profile') and user.phlebotomist_profile.approved == False:
                    return Response({"success": False, "message": "Your account is rejected."}, status=status.HTTP_404_NOT_FOUND)
                
                if user.role == 'client' and hasattr(user, 'client_profile') and user.client_profile.is_approved == None:
                    return Response({"success": False, "message": "Your account is not approved yet."}, status=status.HTTP_404_NOT_FOUND)
                
                if user.role == 'client' and hasattr(user, 'client_profile') and user.client_profile.is_approved == False:
                    return Response({"success": False, "message": "Your account is rejected."}, status=status.HTTP_404_NOT_FOUND)
                
                if user.suspended:
                    return Response({"success": False, "message": "Your account is suspended."}, status=status.HTTP_404_NOT_FOUND)
                
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


class ProfileAPIView(NewAPIView):
    serializer_class = serializers.EmptySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['Authentication'])
    def get(self, request):
        """
        **Profile Endpoint - Private**\n
        Retrieve the profile details of the authenticated user.
        """
        return Response({"success": True, "message": "Profile details retrieved successfully.", "data": serializers.UserSerializer(request.user, context={'request': request}).data}, status=status.HTTP_200_OK)


# Phlebotomist Profile Update View
class PhlebotomistProfileUpdateView(NewAPIView):
    serializer_class = serializers.EmptySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['patch']

    @swagger_auto_schema(
        tags=['App - Profile Management'],
        manual_parameters=[
            openapi.Parameter('full_name',            openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('phone_number',         openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('gender',               openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, enum=['male', 'female']),
            openapi.Parameter('dob',                  openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, description='YYYY-MM-DD'),
            openapi.Parameter('profile_picture',      openapi.IN_FORM, type=openapi.TYPE_FILE,    required=False),
            openapi.Parameter('license_number',       openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('license_expiry_date',  openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, description='YYYY-MM-DD'),
            openapi.Parameter('years_of_experience',  openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('specialty',            openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, enum=['general_phlebotomy', 'iv_insertion_or_therapy', 'oncology_or_chemotherapy', 'medical_nurse']),
            openapi.Parameter('work_preference',      openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, enum=['part_time', 'full_time']),
            openapi.Parameter('service_area',         openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('address',              openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('skills',               openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, description='JSON array of skill names, e.g. ["venipuncture","iv_insertion"]'),
            openapi.Parameter('availabilities',       openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, description='JSON array of slots: [{"day":"Monday","date":"2025-09-01","start_time":"09:00","end_time":"17:00","is_available":true}]'),
        ],
        consumes=['multipart/form-data'],
    )
    def patch(self, request):
        """
        **Update Phlebotomist Profile - Phlebotomist Only**\n
        Allows authenticated phlebotomists to update their own profile information.
        All fields are optional — send only what you want to change.\n

        ### Editable User Fields:
        - `full_name` (string)
        - `phone_number` (string)
        - `gender` (string): `male`, `female`
        - `dob` (date): `YYYY-MM-DD`
        - `profile_picture` (file)

        ### Editable Profile Fields:
        - `license_number` (string)
        - `license_expiry_date` (date): `YYYY-MM-DD`
        - `years_of_experience` (integer)
        - `specialty` (string)
        - `work_preference` (string)
        - `service_area` (string)
        - `address` (string)
        - `skills` (list): replaces all skills
        - `availabilities` (list): replaces all availability slots

        ### Restricted Fields (cannot update):
        - `email`, `role`, `suspended`, `approved`, `password` (use separate change password endpoint)

        ### Example Request:
        ```json
        {Allows authenticated phlebotomists to update their own profile information.

            "full_name": "Jane Doe",
            "phone_number": "1234567890",
            "years_of_experience": 5,
            "skills": ["venipuncture", "iv_insertion"]
        }
        ```

        ### Responses:
        - **200 OK**: Profile updated successfully.
        - **400 Bad Request**: Validation error.
        - **403 Forbidden**: User is not a phlebotomist.
        """
        user = request.user
        if user.role != 'phlebotomist':
            return Response(
                {"detail": "Only phlebotomists can use this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = user.phlebotomist_profile
        except Exception:
            return Response(
                {"detail": "Phlebotomist profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data
        errors = {}

        def get_valid_value(key, current_val, is_nullable=False):
            if key not in data:
                return current_val, False
            val = data[key]
            if isinstance(val, str):
                val = val.strip()
                if val.lower() in ('null', 'undefined'):
                    val = ''
            if val == '' or val is None:
                if is_nullable:
                    return None, current_val is not None
                return current_val, False
            
            if isinstance(current_val, str) and not isinstance(val, str):
                val_str = str(val)
            else:
                val_str = val
            return val, val_str != current_val

        # ── User fields ───────────────────────────────────────────────────────
        user_dirty = False

        val, updated = get_valid_value('full_name', user.full_name)
        if updated:
            user.full_name = val
            user_dirty = True

        val, updated = get_valid_value('phone_number', user.phone_number)
        if updated:
            user.phone_number = val
            user_dirty = True

        val, updated = get_valid_value('gender', user.gender)
        if updated:
            valid = [c[0] for c in models.User.GENDER_CHOICES]
            if val not in valid:
                errors['gender'] = [f"Invalid choice. Valid options: {valid}"]
            else:
                user.gender = val
                user_dirty = True

        val, updated = get_valid_value('dob', user.dob)
        if updated:
            import datetime
            try:
                if isinstance(val, (datetime.date, datetime.datetime)):
                    user.dob = val
                else:
                    user.dob = datetime.date.fromisoformat(str(val))
                user_dirty = True
            except ValueError:
                errors['dob'] = ["Invalid date format. Use YYYY-MM-DD."]

        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
            user_dirty = True

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # ── Profile fields ────────────────────────────────────────────────────
        profile_dirty = False

        val, updated = get_valid_value('license_number', profile.license_number)
        if updated:
            profile.license_number = val
            profile_dirty = True

        val, updated = get_valid_value('license_expiry_date', profile.license_expiry_date)
        if updated:
            import datetime
            try:
                if isinstance(val, (datetime.date, datetime.datetime)):
                    profile.license_expiry_date = val
                else:
                    profile.license_expiry_date = datetime.date.fromisoformat(str(val))
                profile_dirty = True
            except ValueError:
                errors['license_expiry_date'] = ["Invalid date format. Use YYYY-MM-DD."]

        val, updated = get_valid_value('years_of_experience', profile.years_of_experience)
        if updated:
            try:
                val_int = int(val)
                if val_int < 0:
                    errors['years_of_experience'] = ["Must be non-negative."]
                else:
                    profile.years_of_experience = val_int
                    profile_dirty = True
            except (ValueError, TypeError):
                errors['years_of_experience'] = ["Enter a valid integer."]

        val, updated = get_valid_value('specialty', profile.specialty)
        # if updated:
        #     valid = [c[0] for c in models.Phlebotomist.SPECIALTY_CHOICES]
        #     if val not in valid:
        #         errors['specialty'] = [f"Invalid choice. Valid options: {valid}"]
        #     else:
        #         profile.specialty = val
        #         profile_dirty = True

        val, updated = get_valid_value('work_preference', profile.work_preference)
        if updated:
            valid = [c[0] for c in models.Phlebotomist.WORK_PREFERENCE_CHOICES]
            if val not in valid:
                errors['work_preference'] = [f"Invalid choice. Valid options: {valid}"]
            else:
                profile.work_preference = val
                profile_dirty = True

        val, updated = get_valid_value('service_area', profile.service_area)
        if updated:
            profile.service_area = val
            profile_dirty = True

        val, updated = get_valid_value('address', profile.address, is_nullable=True)
        if updated:
            profile.address = val
            profile_dirty = True

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        from django.db import transaction
        try:
            with transaction.atomic():
                if user_dirty:
                    user.save()
                if profile_dirty:
                    profile.save()

                # ── Skills: full replace ──────────────────────────────────────
                if 'skills' in data:
                    raw = data['skills']
                    if isinstance(raw, str):
                        raw = raw.strip()
                        if raw.lower() in ('null', 'undefined'):
                            raw = ''
                    if raw not in ('', None):
                        if isinstance(raw, str):
                            import json as json_mod
                            try:
                                raw = json_mod.loads(raw)
                            except json_mod.JSONDecodeError:
                                return Response({'skills': ["Invalid JSON format."]}, status=status.HTTP_400_BAD_REQUEST)
                        if not isinstance(raw, list):
                            return Response({'skills': ["Must be a list."]}, status=status.HTTP_400_BAD_REQUEST)
                        profile.skills.all().delete()
                        for skill_name in raw:
                            if skill_name:
                                models.Phlebotomist_skill.objects.get_or_create(phlebotomist=profile, skill_name=skill_name.strip())

                # ── Availabilities: full replace ──────────────────────────────
                if 'availabilities' in data:
                    raw = data['availabilities']
                    if isinstance(raw, str):
                        raw = raw.strip()
                        if raw.lower() in ('null', 'undefined'):
                            raw = ''
                    if raw not in ('', None):
                        if isinstance(raw, str):
                            import json as json_mod
                            try:
                                raw = json_mod.loads(raw)
                            except json_mod.JSONDecodeError:
                                return Response({'availabilities': ["Invalid JSON format."]}, status=status.HTTP_400_BAD_REQUEST)
                        if not isinstance(raw, list):
                            return Response({'availabilities': ["Must be a list."]}, status=status.HTTP_400_BAD_REQUEST)
                        profile.availabilities.all().delete()
                        import datetime
                        for slot in raw:
                            try:
                                models.PhlebotomistAvailability.objects.create(
                                    phlebotomist=profile,
                                    day=slot['day'],
                                    date=datetime.date.fromisoformat(slot['date']),
                                    start_time=datetime.time.fromisoformat(slot['start_time']),
                                    end_time=datetime.time.fromisoformat(slot['end_time']),
                                    is_available=slot.get('is_available', True),
                                )
                            except (KeyError, ValueError) as e:
                                raise ValueError(f"Invalid slot data: {e}")
        except ValueError as e:
            return Response({'availabilities': [str(e)]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Profile updated successfully."}, status=status.HTTP_200_OK)


# Client Profile Update View
class ClientProfileUpdateView(NewAPIView):
    serializer_class = serializers.EmptySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['patch']

    @swagger_auto_schema(
        tags=['App - Profile Management'],
        manual_parameters=[
            openapi.Parameter('full_name',                  openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('phone_number',               openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('gender',                     openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, enum=['male', 'female']),
            openapi.Parameter('dob',                        openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, description='YYYY-MM-DD'),
            openapi.Parameter('profile_picture',            openapi.IN_FORM, type=openapi.TYPE_FILE,    required=False),
            openapi.Parameter('business_name',              openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('business_type',              openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, enum=['healthcare', 'individual']),
            openapi.Parameter('business_address_street',    openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('business_address_city',      openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('business_address_state',     openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('business_address_zip',       openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('contact_person_name',        openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('business_phone',             openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('business_license_number',    openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('business_description',       openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False),
            openapi.Parameter('hourly_pay_rate',            openapi.IN_FORM, type=openapi.TYPE_NUMBER,  required=False),
            openapi.Parameter('preferred_job_type',         openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, enum=['in_clinic_phlebotomy', 'mobile_blood_draw', 'laboratory_testing']),
            openapi.Parameter('work_preference',            openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, enum=['part_time', 'full_time']),
            openapi.Parameter('availabilities',             openapi.IN_FORM, type=openapi.TYPE_STRING,  required=False, description='JSON array of slots: [{"day":"Monday","date":"2025-09-01","start_time":"09:00","end_time":"17:00","is_available":true}]'),
        ],
        consumes=['multipart/form-data'],
    )
    def patch(self, request):
        """
        **Update Client Profile - Client Only**\n
        Allows authenticated clients to update their own profile information.
        All fields are optional — send only what you want to change.\n

        ### Editable User Fields:
        - `full_name` (string)
        - `phone_number` (string)
        - `gender` (string): `male`, `female`
        - `dob` (date): `YYYY-MM-DD`
        - `profile_picture` (file)

        ### Editable Profile Fields:
        - `business_name` (string)
        - `business_type` (string)
        - `business_address_street` (string)
        - `business_address_city` (string)
        - `business_address_state` (string)
        - `business_address_zip` (string)
        - `contact_person_name` (string)
        - `business_phone` (string)
        - `business_license_number` (string)
        - `business_description` (string)
        - `hourly_pay_rate` (decimal)
        - `preferred_job_type` (string)
        - `work_preference` (string)
        - `no_of_employees` (integer)
        - `availabilities` (list): replaces all availability slots

        ### Restricted Fields (cannot update):
        - `email`, `role`, `suspended`, `is_approved`, `signature`, `password`

        ### Example Request:
        ```json
        {
            "business_name": "New Clinic Name",
            "business_address_city": "Los Angeles",
            "hourly_pay_rate": "35.00"
        }
        ```

        ### Responses:
        - **200 OK**: Profile updated successfully.
        - **400 Bad Request**: Validation error.
        - **403 Forbidden**: User is not a client.
        """
        user = request.user
        if user.role != 'client':
            return Response(
                {"detail": "Only clients can use this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = user.client_profile
        except Exception:
            return Response(
                {"detail": "Client profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data
        errors = {}

        def get_valid_value(key, current_val, is_nullable=False):
            if key not in data:
                return current_val, False
            val = data[key]
            if isinstance(val, str):
                val = val.strip()
                if val.lower() in ('null', 'undefined'):
                    val = ''
            if val == '' or val is None:
                if is_nullable:
                    return None, current_val is not None
                return current_val, False
            
            if isinstance(current_val, str) and not isinstance(val, str):
                val_str = str(val)
            else:
                val_str = val
            return val, val_str != current_val

        # ── User fields ───────────────────────────────────────────────────────
        user_dirty = False

        val, updated = get_valid_value('full_name', user.full_name)
        if updated:
            user.full_name = val
            user_dirty = True

        val, updated = get_valid_value('phone_number', user.phone_number)
        if updated:
            user.phone_number = val
            user_dirty = True

        val, updated = get_valid_value('gender', user.gender)
        if updated:
            valid = [c[0] for c in models.User.GENDER_CHOICES]
            if val not in valid:
                errors['gender'] = [f"Invalid choice. Valid options: {valid}"]
            else:
                user.gender = val
                user_dirty = True

        val, updated = get_valid_value('dob', user.dob)
        if updated:
            import datetime
            try:
                if isinstance(val, (datetime.date, datetime.datetime)):
                    user.dob = val
                else:
                    user.dob = datetime.date.fromisoformat(str(val))
                user_dirty = True
            except ValueError:
                errors['dob'] = ["Invalid date format. Use YYYY-MM-DD."]

        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
            user_dirty = True

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # ── Profile validation choices ─────────────────────────────────────────
        profile_dirty = False

        val_business_type, updated_business_type = get_valid_value('business_type', profile.business_type)
        if updated_business_type:
            # valid = [c[0] for c in models.Client.BUSINESS_TYPE_CHOICES]
            # if val_business_type not in valid:
            #     errors['business_type'] = [f"Invalid choice. Valid options: {valid}"]
            if not val_business_type or len(val_business_type.strip()) == 0:
                errors['business_type'] = ["This field is required."]

        val_pref_job, updated_pref_job = get_valid_value('preferred_job_type', profile.preferred_job_type)
        if updated_pref_job:
            # valid = [c[0] for c in models.Client.JOB_PREFERENCE_CHOICES]
            # if val_pref_job not in valid:
            #     errors['preferred_job_type'] = [f"Invalid choice. Valid options: {valid}"]
            if not val_pref_job or len(val_pref_job.strip()) == 0:
                errors['preferred_job_type'] = ["This field is required."]

        val_work_pref, updated_work_pref = get_valid_value('work_preference', profile.work_preference)
        if updated_work_pref:
            # valid = [c[0] for c in models.Client.WORK_PREFERENCE_CHOICES]
            # if val_work_pref not in valid:
            if not val_work_pref or len(val_work_pref.strip()) == 0:
                errors['work_preference'] = ["This field is required."]
    
        val_employees, updated_employees = get_valid_value('no_of_employees', profile.no_of_employees)
        if updated_employees:
            try:
                val_int = int(val_employees)
                if val_int < 0:
                    errors['no_of_employees'] = ["Must be non-negative."]
            except (ValueError, TypeError):
                errors['no_of_employees'] = ["Enter a valid integer."]

        val_rate, updated_rate = get_valid_value('hourly_pay_rate', profile.hourly_pay_rate)
        if updated_rate:
            from decimal import Decimal, InvalidOperation
            try:
                val_dec = Decimal(str(val_rate))
                if val_dec < 0:
                    errors['hourly_pay_rate'] = ["Must be a positive value."]
            except InvalidOperation:
                errors['hourly_pay_rate'] = ["Enter a valid decimal number."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # ── Profile fields update ─────────────────────────────────────────────
        from django.db import transaction
        from decimal import Decimal

        try:
            with transaction.atomic():
                if user_dirty:
                    user.save()

                str_fields = [
                    'business_name', 'business_address_street',
                    'business_address_city', 'business_address_state', 'business_address_zip',
                    'contact_person_name', 'business_phone', 'business_license_number',
                    'business_description',
                ]
                for field in str_fields:
                    val_str, updated_str = get_valid_value(field, getattr(profile, field))
                    if updated_str:
                        setattr(profile, field, val_str)
                        profile_dirty = True

                if updated_business_type:
                    profile.business_type = val_business_type
                    profile_dirty = True
                if updated_pref_job:
                    profile.preferred_job_type = val_pref_job
                    profile_dirty = True
                if updated_work_pref:
                    profile.work_preference = val_work_pref
                    profile_dirty = True
                if updated_employees:
                    profile.no_of_employees = int(val_employees)
                    profile_dirty = True
                if updated_rate:
                    profile.hourly_pay_rate = Decimal(str(val_rate))
                    profile_dirty = True

                if profile_dirty:
                    profile.save()

                # ── Availabilities: full replace ──────────────────────────────
                if 'availabilities' in data:
                    raw = data['availabilities']
                    if isinstance(raw, str):
                        raw = raw.strip()
                        if raw.lower() in ('null', 'undefined'):
                            raw = ''
                    if raw not in ('', None):
                        if isinstance(raw, str):
                            import json as json_mod
                            try:
                                raw = json_mod.loads(raw)
                            except json_mod.JSONDecodeError:
                                return Response({'availabilities': ["Invalid JSON format."]}, status=status.HTTP_400_BAD_REQUEST)
                        if not isinstance(raw, list):
                            return Response({'availabilities': ["Must be a list."]}, status=status.HTTP_400_BAD_REQUEST)
                        profile.availabilities.all().delete()
                        import datetime
                        for slot in raw:
                            try:
                                models.ClientWeeklySchedule.objects.create(
                                    client=profile,
                                    day=slot['day'],
                                    date=datetime.date.fromisoformat(slot['date']),
                                    start_time=datetime.time.fromisoformat(slot['start_time']),
                                    end_time=datetime.time.fromisoformat(slot['end_time']),
                                    is_available=slot.get('is_available', True),
                                )
                            except (KeyError, ValueError) as e:
                                raise ValueError(f"Invalid slot data: {e}")
        except ValueError as e:
            return Response({'availabilities': [str(e)]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Profile updated successfully."}, status=status.HTTP_200_OK)


class PhlebotomistProfileView(NewAPIView):
    serializer_class = serializers.EmptySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['App - Profile Management'])
    def get(self, request):
        """
        **Get Phlebotomist Profile - Phlebotomist Only**\n
        Returns the full profile of the authenticated phlebotomist including
        credentials, skills, activity stats, and ratings & reviews.\n

        ### Response Sections:
        - **header**: Name, specialty, profile picture, rating summary, gender.
        - **stats**: Jobs completed, success rate, years of experience.
        - **credentials**: License and certification documents with approval and expiry.
        - **skills**: List of skill names.
        - **ratings_and_reviews**: Overall rating, total reviews, and recent review list.

        ### Example Response:
        ```json
        {
            "header": {
                "full_name": "FA Kabita",
                "specialty": "general_phlebotomy",
                "profile_picture": "http://localhost:8000/media/profile_pictures/kabita.jpg",
                "overall_rating": 4.9,
                "total_reviews": 127,
                "gender": "female"
            },
            "stats": {
                "jobs_completed": 247,
                "success_rate": "98%",
                "years_of_experience": 3
            },
            "credentials": [
                {
                    "id": 1,
                    "document_name": "license",
                    "approved": true,
                    "expiry_date": "12/2025",
                    "document_file": "http://localhost:8000/media/phlebotomist_documents/license.pdf"
                }
            ],
            "skills": ["Blood Collection", "IV Insertion"],
            "ratings_and_reviews": {
                "overall_rating": 4.9,
                "total_reviews": 127,
                "reviews": [
                    {
                        "reviewer_name": "Fariha Tasnim",
                        "reviewer_picture": null,
                        "rating": 5,
                        "comment": "Excellent service! Highly recommend.",
                        "reviewed_ago": "2 days ago"
                    }
                ]
            }
        }
        ```

        ### Responses:
        - **200 OK**: Profile returned.
        - **403 Forbidden**: User is not a phlebotomist.
        - **404 Not Found**: Profile not found.
        """
        from django.utils.timezone import now
        from datetime import timedelta
        from django.db.models import Avg, Count
        from jobs.models import JobAssignment
        from communication.models import Review

        user = request.user

        if user.role != 'phlebotomist':
            return Response(
                {"detail": "Only phlebotomists can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = user.phlebotomist_profile
        except Exception:
            return Response(
                {"detail": "Phlebotomist profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # ── Relative time helper ──────────────────────────────────────────────
        def time_ago(dt):
            delta = now() - dt
            if delta < timedelta(minutes=1):
                return "just now"
            elif delta < timedelta(hours=1):
                m = int(delta.total_seconds() / 60)
                return f"{m} minute{'s' if m != 1 else ''} ago"
            elif delta < timedelta(days=1):
                h = int(delta.total_seconds() / 3600)
                return f"{h} hour{'s' if h != 1 else ''} ago"
            elif delta < timedelta(days=30):
                return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
            elif delta < timedelta(days=365):
                mo = int(delta.days / 30)
                return f"{mo} month{'s' if mo != 1 else ''} ago"
            else:
                yr = int(delta.days / 365)
                return f"{yr} year{'s' if yr != 1 else ''} ago"

        # ── Stats ─────────────────────────────────────────────────────────────
        total_assignments  = user.assignments.count()
        completed_assignments = user.assignments.filter(status='completed').count()
        success_rate = (
            f"{round((completed_assignments / total_assignments) * 100)}%"
            if total_assignments > 0 else "0%"
        )

        # ── Ratings & Reviews ─────────────────────────────────────────────────
        reviews_qs = Review.objects.filter(
            reviewed=user,
            status=Review.APPROVED
        ).select_related('reviewer').order_by('-created_at')

        rating_data  = reviews_qs.aggregate(avg=Avg('rating'), total=Count('id'))
        overall_rating = round(rating_data['avg'] or 0, 1)
        total_reviews  = rating_data['total']

        recent_reviews = [
            {
                "reviewer_name":    r.reviewer.full_name,
                "reviewer_picture": request.build_absolute_uri(r.reviewer.profile_picture.url) if r.reviewer.profile_picture else None,
                "rating":           r.rating,
                "comment":          r.comment,
                "reviewed_ago":     time_ago(r.created_at),
            }
            for r in reviews_qs[:10]
        ]

        # ── Credentials ───────────────────────────────────────────────────────
        credentials = [
            {
                "id":            doc.id,
                "document_name": doc.document_name,
                "approved":      doc.approved,
                "expiry_date":   profile.license_expiry_date.strftime("%m/%Y") if doc.document_name == 'license' else None,
                "document_file": request.build_absolute_uri(doc.document_file.url),
            }
            for doc in profile.documents.all()
        ]

        return Response(
            {
                "header": {
                    "full_name":       user.full_name,
                    "specialty":       profile.specialty,
                    "profile_picture": request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
                    "overall_rating":  overall_rating,
                    "total_reviews":   total_reviews,
                    "phone_number":    user.phone_number,
                    "gender":          user.gender,
                },
                "stats": {
                    "jobs_completed":     completed_assignments,
                    "success_rate":       success_rate,
                    "years_of_experience": profile.years_of_experience,
                },
                "credentials":  credentials,
                "skills":       [s.skill_name for s in profile.skills.all()],
                "ratings_and_reviews": {
                    "overall_rating": overall_rating,
                    "total_reviews":  total_reviews,
                    "reviews":        recent_reviews,
                },
            },
            status=status.HTTP_200_OK
        )


# Client Profile Get View
class ClientProfileView(NewAPIView):
    serializer_class = serializers.EmptySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['App - Profile Management'])
    def get(self, request):
        """
        **Get Client Profile - Client Only**\n
        Returns the full profile of the authenticated client including
        business information, documents, activity stats, and ratings & reviews.\n

        ### Response Sections:
        - **header**: Name, business type, profile picture, rating summary, gender.
        - **stats**: Jobs posted, jobs completed, active jobs.
        - **business_information**: Full business address, contact details, pay rate, etc.
        - **documents**: Uploaded business documents with approval status.
        - **ratings_and_reviews**: Overall rating, total reviews, and recent review list.

        ### Responses:
        - **200 OK**: Profile returned.
        - **403 Forbidden**: User is not a client.
        - **404 Not Found**: Profile not found.
        """
        from django.utils.timezone import now
        from datetime import timedelta
        from django.db.models import Avg, Count
        from jobs.models import Job
        from communication.models import Review

        user = request.user

        if user.role != 'client':
            return Response(
                {"detail": "Only clients can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = user.client_profile
        except Exception:
            return Response(
                {"detail": "Client profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # ── Relative time helper ──────────────────────────────────────────────
        def time_ago(dt):
            delta = now() - dt
            if delta < timedelta(minutes=1):
                return "just now"
            elif delta < timedelta(hours=1):
                m = int(delta.total_seconds() / 60)
                return f"{m} minute{'s' if m != 1 else ''} ago"
            elif delta < timedelta(days=1):
                h = int(delta.total_seconds() / 3600)
                return f"{h} hour{'s' if h != 1 else ''} ago"
            elif delta < timedelta(days=30):
                return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
            elif delta < timedelta(days=365):
                mo = int(delta.days / 30)
                return f"{mo} month{'s' if mo != 1 else ''} ago"
            else:
                yr = int(delta.days / 365)
                return f"{yr} year{'s' if yr != 1 else ''} ago"

        # ── Stats ─────────────────────────────────────────────────────────────
        all_jobs       = user.jobs.all()
        total_posted   = all_jobs.count()
        total_completed = all_jobs.filter(status='completed').count()
        total_active   = all_jobs.filter(status__in=['open', 'in_progress']).count()

        # ── Ratings & Reviews ─────────────────────────────────────────────────
        reviews_qs = Review.objects.filter(
            reviewed=user,
            status = Review.APPROVED
        ).select_related('reviewer').order_by('-created_at')

        rating_data    = reviews_qs.aggregate(avg=Avg('rating'), total=Count('id'))
        overall_rating = round(rating_data['avg'] or 0, 1)
        total_reviews  = rating_data['total']

        recent_reviews = [
            {
                "reviewer_name":    r.reviewer.full_name,
                "reviewer_picture": request.build_absolute_uri(r.reviewer.profile_picture.url) if r.reviewer.profile_picture else None,
                "rating":           r.rating,
                "comment":          r.comment,
                "reviewed_ago":     time_ago(r.created_at),
            }
            for r in reviews_qs[:10]
        ]

        # ── Documents ─────────────────────────────────────────────────────────
        documents = [
            {
                "id":            doc.id,
                "document_name": doc.document_name,
                "approved":      doc.approved,
                "document_file": request.build_absolute_uri(doc.document_file.url),
                "uploaded_on":   doc.created_at.strftime("%b %d, %Y"),
            }
            for doc in profile.documents.all()
        ]

        return Response(
            {
                "header": {
                    "full_name":       user.full_name,
                    "business_type":   profile.business_type,
                    "profile_picture": request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
                    "overall_rating":  overall_rating,
                    "total_reviews":   total_reviews,
                    "gender":          user.gender,
                    "phone_number":    user.phone_number,
                    "email":           user.email,
                    "member_since":    user.created_at.strftime("%B %Y"),
                },
                "stats": {
                    "jobs_posted":    total_posted,
                    "jobs_completed": total_completed,
                    "active_jobs":    total_active,
                },
                "business_information": {
                    "business_name":           profile.business_name,
                    "business_type":           profile.business_type,
                    "business_address_street": profile.business_address_street,
                    "business_address_city":   profile.business_address_city,
                    "business_address_state":  profile.business_address_state,
                    "business_address_zip":    profile.business_address_zip,
                    "contact_person_name":     profile.contact_person_name,
                    "business_phone":          profile.business_phone,
                    "business_license_number": profile.business_license_number,
                    "business_description":    profile.business_description,
                    "hourly_pay_rate":         str(profile.hourly_pay_rate),
                    "preferred_job_type":      profile.preferred_job_type,
                    "work_preference":         profile.work_preference,
                    "no_of_employees":         profile.no_of_employees,
                },
                "documents": documents,
                "ratings_and_reviews": {
                    "overall_rating": overall_rating,
                    "total_reviews":  total_reviews,
                    "reviews":        recent_reviews,
                },
            },
            status=status.HTTP_200_OK
        )
