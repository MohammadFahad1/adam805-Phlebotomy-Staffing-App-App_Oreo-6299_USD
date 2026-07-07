from django.contrib import admin
from .models import Job, JobApplication, JobAssignment, JobTemplate


# --- Inlines for Job Management ---

class JobApplicationInline(admin.TabularInline):
    model = JobApplication
    extra = 0
    raw_id_fields = ('phlebotomist',)
    readonly_fields = ('applied_at',)


class JobAssignmentInline(admin.StackedInline):
    model = JobAssignment
    extra = 0
    raw_id_fields = ('phlebotomist', 'client')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': (('phlebotomist', 'client'), 'status')
        }),
        ('Contract Compliance', {
            'fields': (('signed_by_phlebotomist', 'signed_by_client'), 'contract_url')
        }),
        ('Execution Windows', {
            'fields': (('start_time', 'end_time'),)
        }),
    )


# --- Model Admins ---

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'title', 
        'get_client_name', 
        'shift_date', 
        'professional_type', 
        'pay_rate', 
        'pay_type', 
        'status', 
        'created_at'
    )
    list_filter = ('status', 'professional_type', 'job_type', 'pay_type', 'shift_date', 'created_at')
    search_fields = ('id', 'title', 'city', 'client__full_name', 'client__email')
    list_editable = ('status',)  # Change job life-cycles on the fly without entering detail menus
    raw_id_fields = ('client',)
    
    inlines = [JobApplicationInline, JobAssignmentInline]
    
    fieldsets = (
        ('Overview', {
            'fields': ('id', 'client', 'title', 'description', 'status')
        }),
        ('Logistics & Shift Schedule', {
            'fields': ('location', 'city', 'shift_date', ('shift_start', 'shift_end'), ('shift_duration', 'duration_hours'))
        }),
        ('Compensation & Role Specifics', {
            'fields': (('pay_type', 'pay_rate'), ('professional_type', 'job_type'))
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # Primary key custom logic means ID is evaluated uniquely, keeping it safe
    readonly_fields = ('id', 'created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client')

    @admin.display(ordering='client__full_name', description='Client Email / Name')
    def get_client_name(self, obj):
        return f"{obj.client.full_name} ({obj.client.email})"


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'get_phlebotomist_info', 'status', 'applied_at')
    list_filter = ('status', 'applied_at')
    list_editable = ('status',)
    search_fields = ('job__id', 'job__title', 'phlebotomist__full_name', 'phlebotomist__email')
    raw_id_fields = ('job', 'phlebotomist')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('job', 'phlebotomist')

    @admin.display(ordering='phlebotomist__full_name', description='Phlebotomist')
    def get_phlebotomist_info(self, obj):
        return f"{obj.phlebotomist.full_name} ({obj.phlebotomist.email})"


@admin.register(JobAssignment)
class JobAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'job', 
        'get_phlebotomist_name', 
        'get_client_name', 
        'status', 
        'signed_by_phlebotomist', 
        'signed_by_client', 
        'created_at'
    )
    list_filter = ('status', 'signed_by_phlebotomist', 'signed_by_client', 'created_at')
    list_editable = ('status',)
    search_fields = ('job__id', 'job__title', 'phlebotomist__full_name', 'client__full_name')
    raw_id_fields = ('job', 'phlebotomist', 'client')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('job', 'phlebotomist', 'client')

    @admin.display(ordering='phlebotomist__full_name', description='Phlebotomist')
    def get_phlebotomist_name(self, obj):
        return obj.phlebotomist.full_name

    @admin.display(ordering='client__full_name', description='Client')
    def get_client_name(self, obj):
        return obj.client.full_name


@admin.register(JobTemplate)
class JobTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'city', 'professional_type', 'pay_rate', 'pay_type', 'status')
    list_filter = ('status', 'professional_type', 'pay_type')
    search_fields = ('title', 'city', 'description')
    
    fieldsets = (
        ('Template Core', {
            'fields': ('title', 'description', 'status')
        }),
        ('Default Requirements & Logistics', {
            'fields': ('location', 'city', 'shift_date', ('shift_start', 'shift_end'), ('shift_duration', 'duration_hours'))
        }),
        ('Financials & Classification', {
            'fields': (('pay_type', 'pay_rate'), ('professional_type', 'job_type'))
        }),
    )

