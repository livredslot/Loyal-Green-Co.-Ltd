from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Customer, Price, PriceGroup


@admin.register(PriceGroup)
class PriceGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "order")


@admin.register(Customer)
class CustomerAdmin(SimpleHistoryAdmin):
    list_display = ("name", "type", "price_group", "payment_terms_days", "credit_limit", "is_active")
    list_filter = ("type", "price_group", "is_active")
    search_fields = ("name", "tax_no", "contact_person", "phone")


@admin.register(Price)
class PriceAdmin(SimpleHistoryAdmin):
    list_display = ("item", "price_group", "customer", "unit", "price", "min_qty", "valid_from", "valid_to")
    list_filter = ("price_group", "unit")
    search_fields = ("item__code", "item__name_en", "customer__name")
    autocomplete_fields = ("item", "customer")
