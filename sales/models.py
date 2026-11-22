from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from inventory.models import Item, Unit


class PriceGroup(models.Model):
    name = models.CharField(max_length=60, unique=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Customer(models.Model):
    class Type(models.TextChoices):
        SUPERMARKET = "Supermarket", "Supermarket"
        CONVENIENCE = "Convenience", "Convenience store"
        WHOLESALE = "Wholesale", "Wholesale"
        RETAIL = "Retail", "Retail shop"
        HOTEL = "Hotel", "Hotel / restaurant"
        COMPANY = "Company", "Company"

    name = models.CharField(max_length=200, unique=True)
    type = models.CharField(max_length=20, choices=Type.choices)
    price_group = models.ForeignKey(PriceGroup, on_delete=models.PROTECT, null=True, blank=True, related_name="customers")
    tax_no = models.CharField("Tax no.", max_length=50, blank=True)
    billing_address = models.TextField(blank=True)
    delivery_address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    payment_terms_days = models.PositiveSmallIntegerField(
        "Payment terms (days)", default=0, help_text="0 = cash / cash on delivery."
    )
    credit_limit = models.PositiveBigIntegerField(
        "Credit limit (MMK)", null=True, blank=True, help_text="Leave empty if not set yet."
    )
    salesperson = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="customers"
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField("Active", default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("customer_detail", args=[self.pk])

    @property
    def terms_label(self):
        return f"{self.payment_terms_days} days" if self.payment_terms_days else "Cash"


class Price(models.Model):
    """
    A selling price in kyats before Commercial Tax, for a price group or one customer.
    A price change adds a new row from a date; earlier rows stay as price history.
    """

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="prices", limit_choices_to={"type__in": ["FG", "TG"]})
    price_group = models.ForeignKey(PriceGroup, on_delete=models.PROTECT, null=True, blank=True, related_name="prices")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True, related_name="special_prices")
    unit = models.CharField(max_length=5, choices=[(Unit.PKT, "pkt"), (Unit.CTN, "ctn")], default=Unit.PKT)
    price = models.PositiveBigIntegerField("Price (MMK, before tax)")
    min_qty = models.PositiveIntegerField("Minimum quantity for this price", default=1)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["item__code", "-valid_from"]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(price_group__isnull=False, customer__isnull=True)
                           | models.Q(price_group__isnull=True, customer__isnull=False)),
                name="price_for_group_or_customer",
            )
        ]

    def __str__(self):
        who = self.customer or self.price_group
        return f"{self.item.code} {who}: {self.price:,} per {self.unit}"

    def clean(self):
        if bool(self.price_group_id) == bool(self.customer_id):
            raise ValidationError("A price is for either a price group or one customer.")
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValidationError({"valid_to": "Must be on or after the start date."})
