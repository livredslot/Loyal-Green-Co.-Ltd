from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Loyal Green – Admin"
admin.site.site_title = "Loyal Green"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("core.urls")),
]
