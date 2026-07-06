from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, 
    Phlebotomist, 
    PhlebotomistAvailability, 
    Phlebotomist_skill, 
    Phlebotomist_document
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

