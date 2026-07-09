from django.contrib import admin
from appointments.models import ServicePackage, ServicePackageFeature, PatientProfile, Appointment, Payment

# --- Tabular Inlines ---
class ServicePackageFeatureInline(admin.TabularInline):
    model = ServicePackageFeature
    extra = 1
    fields = ('name',)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


class AppointmentInline(admin.TabularInline):
    """Allows viewing a patient's historical or upcoming appointments directly from their profile."""
    model = Appointment
    extra = 0
    fields = ('appointment_date', 'start_time', 'location_type', 'status')
    readonly_fields = ('appointment_date', 'start_time', 'location_type')


# --- Model Admins ---
@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'price')
    ordering = ['price']
    
    inlines = [ServicePackageFeatureInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'email', 'phone_number', 'dob', 'gender', 'created_at')
    list_filter = ('gender', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    ordering = ['-created_at']
    
    inlines = [AppointmentInline]
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(ordering='first_name', description='Patient Name')
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'get_patient_name', 
        'service_package', 
        'appointment_date', 
        'start_time', 
        'location_type', 
        'status'
    )
    list_filter = ('status', 'location_type', 'appointment_date', 'medical_conditions', 'created_at')
    list_editable = ('status',)
    search_fields = (
        'patient__first_name', 
        'patient__last_name', 
        'patient__email', 
        'service_package__name', 
        'location'
    )
    
    # Prevents slow down on large data tables
    inlines = [PaymentInline]
    
    fieldsets = (
        ('Core Assignment & Lifecycle', {
            'fields': ('status', 'patient', 'service_package')
        }),
        ('Schedule & Logistics', {
            'fields': ('appointment_date', ('start_time', 'end_time'), ('location_type', 'location'))
        }),
        ('Medical Information & Attachments', {
            'fields': ('prescription', 'medical_conditions', 'known_allergies', 'current_medications', 'special_requests')
        }),
        ('Communication Preferences', {
            'fields': (('email_result_notification', 'sms_appointment_reminders'),)
        }),
        ('System Log Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    # Optimization: Runs SQL JOIN queries to eliminate N+1 performance bottlenecks
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'service_package')

    @admin.display(ordering='patient__first_name', description='Patient')
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    @admin.display(ordering='phlebotomist__full_name', description='Assigned Phlebotomist')
    def get_phlebotomist_name(self, obj):
        return obj.phlebotomist.full_name if obj.phlebotomist else "—"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_patient_name', 'amount', 'payment_status', 'stripe_payment_id', 'created_at')
    list_filter = ('payment_status', 'created_at')
    list_editable = ('payment_status',)
    search_fields = (
        'stripe_payment_id', 
        'appointment__patient__first_name', 
        'appointment__patient__last_name', 
        'appointment__patient__email'
    )
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('appointment__patient')

    @admin.display(ordering='appointment__patient__first_name', description='Patient Name')
    def get_patient_name(self, obj):
        return f"{obj.appointment.patient.first_name} {obj.appointment.patient.last_name}"


