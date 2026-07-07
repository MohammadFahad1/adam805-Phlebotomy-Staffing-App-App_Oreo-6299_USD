from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from debug_toolbar.toolbar import debug_toolbar_urls

schema_view = get_schema_view(
   openapi.Info(
      title="Phlebotomy Staffing API",
      default_version='v1',
      description="Base URL: http://10.10.13.43:8001",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
   url="https://3m5p7646-8001.inc1.devtunnels.ms"
)

urlpatterns = [
   path('admin/', admin.site.urls),
   path("api-auth/", include("rest_framework.urls")),
   path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
   path('auth/', include('authentication.urls')),
   path('dashboard/', include('dashboard.urls')),
   path('jobs/', include('jobs.urls')),
   path('communication/', include('communication.urls')),
] + debug_toolbar_urls()
