from django.contrib import admin
from .models import Message, Review, Notification, Report


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'receiver', 'job', 'is_read', 'is_seen', 'created_at']
    list_filter = ['is_read', 'is_seen', 'created_at']
    search_fields = ['message_text', 'sender__email', 'sender__username', 
                    'receiver__email', 'receiver__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': ('sender', 'receiver', 'job', 'message_text')
        }),
        ('Status', {
            'fields': ('is_read', 'is_seen')
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'reviewer', 'reviewed', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['comment', 'reviewer__email', 'reviewed__email', 'job__title']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': ('job', 'reviewer', 'reviewed', 'rating', 'comment', 'status')
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__email', 'user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'message', 'type', 'reference_id')
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'reporter', 'reported_user', 'job', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['reason', 'additional_details', 'reporter__email', 
                    'reported_user__email']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'resolved_at']
    
    fieldsets = (
        ('Report Info', {
            'fields': ('reporter', 'reported_user', 'job', 'reason', 'additional_details')
        }),
        ('Admin Review', {
            'fields': ('status', 'admin_notes', 'resolved_by', 'resolved_at')
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Auto set resolved_by when status changes to resolved"""
        if obj.status == 'resolved' and not obj.resolved_by:
            obj.resolved_by = request.user
        super().save_model(request, obj, form, change)

