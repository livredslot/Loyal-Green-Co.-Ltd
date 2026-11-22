from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Category, Item, Location, Machine, Recipe, RecipeLine


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Item)
class ItemAdmin(SimpleHistoryAdmin):
    list_display = ("code", "name_en", "type", "category", "brand", "stock_unit", "pcs_per_pkt", "pkt_per_ctn", "is_active")
    list_filter = ("type", "category", "brand", "is_active")
    search_fields = ("code", "name_en", "name_mm", "barcode")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")


@admin.register(Machine)
class MachineAdmin(SimpleHistoryAdmin):
    list_display = ("name", "output_per_hour", "operators", "hours_per_shift", "is_active")


class RecipeLineInline(admin.TabularInline):
    model = RecipeLine
    extra = 1
    autocomplete_fields = ["material"]


@admin.register(Recipe)
class RecipeAdmin(SimpleHistoryAdmin):
    list_display = ("item", "output_qty", "output_unit", "machine")
    inlines = [RecipeLineInline]
    autocomplete_fields = ["item"]
