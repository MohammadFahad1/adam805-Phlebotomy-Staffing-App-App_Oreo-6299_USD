from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, 
    Phlebotomist, 
    PhlebotomistAvailability, 
    Phlebotomist_skill, 
    Phlebotomist_document,
    Client, 
    ClientDocument, 
    ClientWeeklySchedule,
    ActivityLog
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom UserAdmin configuration since 'username', 'first_name', 
    and 'last_name' fields are removed.
    """
    # Configuration for lists
    list_display = ('id', 'full_name', 'email', 'phone_number', 'role', 'is_staff', 'is_active', 'created_at')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'gender', 'created_at')
    search_fields = ('full_name', 'email', 'phone_number')
    ordering = ('is_superuser', 'is_staff', '-created_at')
    
    # Overriding fieldsets because standard UserAdmin expects username/first_name/last_name
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone_number', 'gender', 'dob', 'profile_picture')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Security / OTP', {'fields': ('otp', 'otp_created_at', 'forgot_password_token'), 'classes': ('collapse',)}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'full_name', 'phone_number', 'role'),
        }),
    )
    # Read-only fields that shouldn't be manually edited directly in those formats
    readonly_fields = ('created_at', 'updated_at', 'otp_created_at')


# --- Tabular Inlines for Phlebotomist Profile ---

class PhlebotomistAvailabilityInline(admin.TabularInline):
    model = PhlebotomistAvailability
    extra = 1
    fields = ('day', 'date', 'start_time', 'end_time', 'is_available')


class PhlebotomistSkillInline(admin.TabularInline):
    model = Phlebotomist_skill
    extra = 1


class PhlebotomistDocumentInline(admin.TabularInline):
    model = Phlebotomist_document
    extra = 1
    fields = ('document_name', 'document_file', 'approved')


# --- Core Profiles & Secondary Models Admin ---

@admin.register(Phlebotomist)
class PhlebotomistAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'license_number', 'license_expiry_date', 'years_of_experience', 'specialty', 'work_preference', 'approved', 'created_at')
    list_filter = ('specialty', 'work_preference', 'approved', 'license_expiry_date')
    search_fields = ('user__full_name', 'user__email', 'license_number', 'service_area')
    list_editable = ('approved',) # Easily approve phlebotomists directly from the list view
    
    # Optimization to prevent N+1 database query issues
    raw_id_fields = ('user',) 
    
    # Attach related profiles directly to the dashboard
    inlines = [PhlebotomistSkillInline, PhlebotomistDocumentInline, PhlebotomistAvailabilityInline]

    @admin.display(ordering='user__full_name', description='Phlebotomist Name')
    def get_name(self, obj):
        return obj.user.full_name


@admin.register(PhlebotomistAvailability)
class PhlebotomistAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('get_phlebotomist_name', 'day', 'date', 'start_time', 'end_time', 'is_available')
    list_filter = ('day', 'date', 'is_available')
    search_fields = ('phlebotomist__user__full_name', 'phlebotomist__user__email')
    raw_id_fields = ('phlebotomist',)

    @admin.display(ordering='phlebotomist__user__full_name', description='Phlebotomist')
    def get_phlebotomist_name(self, obj):
        return obj.phlebotomist.user.full_name


@admin.register(Phlebotomist_skill)
class PhlebotomistSkillAdmin(admin.ModelAdmin):
    list_display = ('skill_name', 'get_phlebotomist_name')
    search_fields = ('skill_name', 'phlebotomist__user__full_name')
    raw_id_fields = ('phlebotomist',)

    @admin.display(ordering='phlebotomist__user__full_name', description='Phlebotomist')
    def get_phlebotomist_name(self, obj):
        return obj.phlebotomist.user.full_name


@admin.register(Phlebotomist_document)
class PhlebotomistDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_name', 'get_phlebotomist_name', 'approved')
    list_filter = ('approved',)
    list_editable = ('approved',)
    search_fields = ('document_name', 'phlebotomist__user__full_name')
    raw_id_fields = ('phlebotomist',)

    @admin.display(ordering='phlebotomist__user__full_name', description='Phlebotomist')
    def get_phlebotomist_name(self, obj):
        return obj.phlebotomist.user.full_name



# --- Tabular Inlines for Client Profile ---

class ClientDocumentInline(admin.TabularInline):
    model = ClientDocument
    extra = 1
    fields = ('document_name', 'document_file', 'approved')


class ClientWeeklyScheduleInline(admin.TabularInline):
    model = ClientWeeklySchedule
    extra = 1
    fields = ('day', 'date', 'start_time', 'end_time', 'is_available')


# --- Core Client & Secondary Models Admin ---

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'get_client_name', 
        'business_name', 
        'business_type', 
        'contact_person_name', 
        'business_phone', 
        'hourly_pay_rate', 
        'is_approved',
        'created_at'
    )
    list_filter = ('business_type', 'preferred_job_type', 'work_preference', 'created_at')
    search_fields = (
        'client__full_name',
        'client__email',
        'business_name', 
        'contact_person_name', 
        'business_license_number'
    )
    
    # Updated to match the new OneToOne field name
    inlines = [ClientDocumentInline, ClientWeeklyScheduleInline]
    
    fieldsets = (
        (None, {
            'fields': ('client',)
        }),
        ('Business Information', {
            'fields': ('business_name', 'business_type', 'business_license_number', 'no_of_employees', 'business_description')
        }),
        ('Contact & Address Details', {
            'fields': ('contact_person_name', 'business_phone', 'business_address_street', 'business_address_city', 'business_address_state', 'business_address_zip')
        }),
        ('Preferences & Rates', {
            'fields': ('hourly_pay_rate', 'preferred_job_type', 'work_preference', 'is_approved')
        }),
        ('System Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(ordering='client__full_name', description='Client Owner Name')
    def get_client_name(self, obj):
        return obj.client.full_name


@admin.register(ClientDocument)
class ClientDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_name', 'get_client_name', 'approved')
    list_filter = ('approved',)
    list_editable = ('approved',)
    search_fields = ('document_name', 'client__client__full_name', 'client__business_name')
    raw_id_fields = ('client',)

    @admin.display(ordering='client__client__full_name', description='Client')
    def get_client_name(self, obj):
        return obj.client.client.full_name


@admin.register(ClientWeeklySchedule)
class ClientWeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ('get_client_name', 'day', 'date', 'start_time', 'end_time', 'is_available')
    list_filter = ('day', 'date', 'is_available')
    search_fields = ('client__client__full_name', 'client__business_name')
    raw_id_fields = ('client',)

    @admin.display(ordering='client__client__full_name', description='Client')
    def get_client_name(self, obj):
        return obj.client.client.full_name


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user_info', 'activity_type', 'description', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('activity_type', 'description', 'user__full_name', 'user__email')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    @admin.display(ordering='user__full_name', description='User')
    def get_user_info(self, obj):
        return f"{obj.user.full_name} ({obj.user.email})"