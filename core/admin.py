from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import CompanyProfile


@admin.register(CompanyProfile)
class CompanyProfileAdmin(SimpleHistoryAdmin):
    def has_add_permission(self, request):
        return not CompanyProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
