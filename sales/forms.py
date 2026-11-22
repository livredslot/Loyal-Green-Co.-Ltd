from datetime import date

from django import forms

from accounts.models import User

from .models import Customer, Price

# Changing these needs the Director's approval (design document, "Approvals")
APPROVAL_FIELDS = ["payment_terms_days", "credit_limit"]


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "name", "type", "price_group", "tax_no", "billing_address", "delivery_address",
            "contact_person", "phone", "email", "payment_terms_days", "credit_limit",
            "salesperson", "notes", "is_active",
        ]
        widgets = {
            "billing_address": forms.Textarea(attrs={"rows": 2}),
            "delivery_address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["salesperson"].queryset = User.objects.filter(is_active=True).order_by("first_name", "username")
        self.can_approve = bool(user and user.has_perm("core.approve_actions"))
        if not self.can_approve:
            for name in APPROVAL_FIELDS:
                del self.fields[name]


class SpecialPriceForm(forms.ModelForm):
    class Meta:
        model = Price
        fields = ["item", "unit", "price", "min_qty", "valid_from", "valid_to", "note"]
        widgets = {"valid_from": forms.DateInput(attrs={"type": "date"}), "valid_to": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = self.fields["item"].queryset.filter(is_active=True)
        self.fields["valid_from"].initial = date.today()


class GroupPricesForm(forms.Form):
    """One packet-price box per item for a price group."""

    valid_from = forms.DateField(
        label="New prices apply from", initial=date.today, widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, items, current, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = items
        for item in items:
            existing = current.get(item.pk)
            self.fields[f"price_{item.pk}"] = forms.IntegerField(
                label=item.code, required=False, min_value=1, initial=existing.price if existing else None
            )

    def rows(self):
        for item in self.items:
            yield item, self[f"price_{item.pk}"]
