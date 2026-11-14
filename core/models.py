from decimal import Decimal

from django.db import models
from simple_history.models import HistoricalRecords


class CompanyProfile(models.Model):
    """
    The company's own details, printed on invoices and other documents.
    There is only ever one row; use CompanyProfile.load().
    """

    name_en = models.CharField("Company name (English)", max_length=200, default="Loyal Green Co., Ltd")
    name_mm = models.CharField("Company name (Myanmar)", max_length=200, blank=True)
    address_en = models.TextField("Address (English)", blank=True)
    address_mm = models.TextField("Address (Myanmar)", blank=True)
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    tax_id = models.CharField("Tax ID (TIN)", max_length=50, blank=True)
    registration_no = models.CharField("Company registration no.", max_length=50, blank=True)
    bank_details = models.TextField("Bank details for invoices", blank=True)
    invoice_footer = models.TextField("Note printed at the bottom of invoices", blank=True)
    logo = models.FileField(upload_to="company/", blank=True)
    commercial_tax_rate = models.DecimalField(
        "Commercial tax %", max_digits=5, decimal_places=2, default=Decimal("5.00")
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "company profile"
        verbose_name_plural = "company profile"
        permissions = [
            ("view_costs", "Can see costs and profit"),
            ("approve_actions", "Can approve discounts, purchases and write-offs"),
        ]

    def __str__(self):
        return self.name_en

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
