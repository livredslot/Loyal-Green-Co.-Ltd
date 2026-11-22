from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(SimpleHistoryAdmin):
    list_display = ("name", "country", "currency", "supplies", "is_active")
    list_filter = ("country", "currency", "is_active")
    search_fields = ("name", "supplies", "contact_person")
