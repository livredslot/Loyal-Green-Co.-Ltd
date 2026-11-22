from django import forms
from django.forms import inlineformset_factory

from .models import Item, Recipe, RecipeLine


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "code", "name_en", "name_mm", "type", "category", "brand", "stock_unit",
            "pcs_per_pkt", "pkt_per_ctn", "weight_per_100_g", "barcode",
            "lead_time_weeks", "safety_stock_weeks", "notes", "is_active",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        data = super().clean()
        unit = data.get("stock_unit")
        if unit == "ctn" and not data.get("pkt_per_ctn"):
            self.add_error("pkt_per_ctn", "Needed when stock is counted in cartons.")
        return data


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ["output_qty", "output_unit", "machine", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


class RecipeLineForm(forms.ModelForm):
    class Meta:
        model = RecipeLine
        fields = ["material", "quantity", "unit", "waste_percent"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["material"].queryset = Item.objects.filter(is_active=True, type__in=["RM", "PK", "TG"])


RecipeLineFormSet = inlineformset_factory(Recipe, RecipeLine, form=RecipeLineForm, extra=3, can_delete=True)
