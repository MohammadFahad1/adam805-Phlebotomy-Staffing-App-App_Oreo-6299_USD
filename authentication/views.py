import json
import re
from rest_framework.response import Response
from rest_framework import status
from phlebotomy_staffing.base import NewAPIView
from authentication import models, serializers
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import AllowAny


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

