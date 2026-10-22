from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # Login, logout and password reset (FR-01).
    path('', include('accounts.auth_urls')),
    path('accounts/', include('accounts.urls')),
    path('allocation/', include('core.allocation_urls')),
    path('', include('core.urls')),
]
