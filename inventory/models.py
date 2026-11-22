from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords


class Unit(models.TextChoices):
    PCS = "pcs", "pcs"
    PKT = "pkt", "pkt"
    CTN = "ctn", "ctn"
    KG = "kg", "kg"
    TON = "ton", "ton"


class ConversionError(ValueError):
    pass


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Item(models.Model):
    """Anything we hold in stock: raw material, packaging, finished good or trading good."""

    class Type(models.TextChoices):
        RAW = "RM", "Raw material"
        PACKAGING = "PK", "Packaging"
        FINISHED = "FG", "Finished good"
        TRADING = "TG", "Trading good"

    code = models.CharField(max_length=30, unique=True)
    name_en = models.CharField("Name (English)", max_length=200)
    name_mm = models.CharField("Name (Myanmar)", max_length=200, blank=True)
    type = models.CharField(max_length=2, choices=Type.choices)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")
    brand = models.CharField(max_length=40, blank=True)
    stock_unit = models.CharField(
        max_length=5, choices=Unit.choices, help_text="The unit stock is counted in: pkt for packed goods, kg for paper."
    )
    pcs_per_pkt = models.PositiveIntegerField("Pcs per pkt", null=True, blank=True)
    pkt_per_ctn = models.PositiveIntegerField("Pkt per ctn", null=True, blank=True)
    weight_per_100_g = models.DecimalField(
        "Weight of 100 pcs (g)", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="For paper fans: lets the system convert kg of paper into pieces.",
    )
    barcode = models.CharField(max_length=40, blank=True)
    lead_time_weeks = models.PositiveIntegerField("Supplier lead time (weeks)", null=True, blank=True)
    safety_stock_weeks = models.PositiveIntegerField("Extra stock to keep (weeks)", null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField("Active", default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.name_en}"

    def get_absolute_url(self):
        return reverse("item_detail", args=[self.pk])

    @property
    def pcs_per_ctn(self):
        if self.pcs_per_pkt and self.pkt_per_ctn:
            return self.pcs_per_pkt * self.pkt_per_ctn
        return None

    @property
    def pcs_per_kg(self):
        if self.weight_per_100_g:
            return (Decimal(100000) / self.weight_per_100_g).quantize(Decimal("0.01"))
        return None

    def _ratios(self):
        """Known unit pairs as (bigger unit, smaller unit, how many smaller in one bigger)."""
        pairs = [(Unit.TON, Unit.KG, Decimal(1000))]
        if self.pcs_per_pkt:
            pairs.append((Unit.PKT, Unit.PCS, Decimal(self.pcs_per_pkt)))
        if self.pkt_per_ctn:
            pairs.append((Unit.CTN, Unit.PKT, Decimal(self.pkt_per_ctn)))
        if self.pcs_per_kg:
            pairs.append((Unit.KG, Unit.PCS, Decimal(100000) / self.weight_per_100_g))
        return pairs

    def convert(self, qty, from_unit, to_unit=None):
        """Convert a quantity between units of this item (default: into its stock unit)."""
        to_unit = to_unit or self.stock_unit
        qty = Decimal(qty)
        if from_unit == to_unit:
            return qty
        edges = {}
        for big, small, n in self._ratios():
            edges.setdefault(big, []).append((small, n))
            edges.setdefault(small, []).append((big, 1 / n))
        # Breadth-first search for a chain of known conversions
        seen, queue = {from_unit}, [(from_unit, Decimal(1))]
        while queue:
            unit, factor = queue.pop(0)
            for nxt, n in edges.get(unit, []):
                if nxt in seen:
                    continue
                if nxt == to_unit:
                    return qty * factor * n
                seen.add(nxt)
                queue.append((nxt, factor * n))
        raise ConversionError(f"{self.code}: cannot convert {from_unit} to {to_unit}; pack sizes are missing.")

    def available_units(self):
        units = []
        for u in Unit:
            try:
                self.convert(1, u)
                units.append(u)
            except ConversionError:
                pass
        return units


class Location(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField("Active", default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.name


class Machine(models.Model):
    name = models.CharField(max_length=100, unique=True)
    output_per_hour = models.PositiveIntegerField("Output per hour (pcs)", null=True, blank=True)
    operators = models.PositiveSmallIntegerField(default=1)
    hours_per_shift = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("8"))
    notes = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField("Active", default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """What one batch of a product uses, normally 1 carton."""

    item = models.OneToOneField(
        Item, on_delete=models.CASCADE, related_name="recipe", limit_choices_to={"type__in": ["FG", "TG"]}
    )
    output_qty = models.DecimalField("Makes", max_digits=10, decimal_places=2, default=Decimal("1"))
    output_unit = models.CharField(max_length=5, choices=Unit.choices, default=Unit.CTN)
    machine = models.ForeignKey(Machine, on_delete=models.SET_NULL, null=True, blank=True, related_name="recipes")
    notes = models.TextField(blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"Recipe for {self.item}"

    def clean(self):
        if self.item_id:
            try:
                self.item.convert(self.output_qty, self.output_unit)
            except ConversionError as e:
                raise ValidationError({"output_unit": str(e)})


class RecipeLine(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="lines")
    material = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name="used_in", limit_choices_to={"type__in": ["RM", "PK", "TG"]}
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=5, choices=Unit.choices)
    waste_percent = models.DecimalField("Normal waste %", max_digits=5, decimal_places=2, default=Decimal("0"))

    history = HistoricalRecords()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.material.name_en}"

    def clean(self):
        if self.material_id and self.unit:
            try:
                self.material.convert(1, self.unit)
            except ConversionError as e:
                raise ValidationError({"unit": str(e)})

    @property
    def stock_qty_with_waste(self):
        """Material taken from stock per batch, in the material's stock unit, including normal waste."""
        net = self.material.convert(self.quantity, self.unit)
        return net * (1 + Decimal(self.waste_percent) / 100)
