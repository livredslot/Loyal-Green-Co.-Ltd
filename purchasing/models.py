from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords


class Currency(models.TextChoices):
    MMK = "MMK", "Kyats (MMK)"
    USD = "USD", "US dollars (USD)"
    CNY = "CNY", "Chinese yuan (CNY)"


class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True)
    country = models.CharField(max_length=60, default="Myanmar")
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.MMK)
    supplies = models.CharField("What they supply", max_length=300, blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    payment_terms = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField("Active", default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("supplier_detail", args=[self.pk])
