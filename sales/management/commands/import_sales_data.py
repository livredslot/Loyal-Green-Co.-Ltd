"""
Load customers, suppliers and group prices from the confirmed Excel file.

    python manage.py import_sales_data "Customers, Suppliers and Prices.xlsx" --dry-run
    python manage.py import_sales_data "Customers, Suppliers and Prices.xlsx"

Each sheet is optional: Customers and Suppliers match on Name, Prices on item Code.
Rows marked Delete in the Check column are skipped. In the Prices sheet, every column
named after a price group holds the packet price (kyats, before tax) for that group.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from inventory.models import Item
from purchasing.models import Currency, Supplier
from sales.models import Customer, Price, PriceGroup


class DryRun(Exception):
    pass


def text(v):
    return "" if v is None else str(v).strip()


def sheet_rows(wb, name):
    """Yield (row number, {header: value}) for a sheet, or nothing if the sheet is missing."""
    if name not in wb.sheetnames:
        return
    rows = wb[name].iter_rows(values_only=True)
    header = [text(h) for h in next(rows)]
    for n, row in enumerate(rows, start=2):
        values = dict(zip(header, row))
        if text(values.get("Check")).lower() == "delete":
            continue
        yield n, values


def to_date(v, field):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(text(v), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{field} must be a date (YYYY-MM-DD), not “{v}”")


def whole(v, field):
    if v in (None, ""):
        return None
    try:
        n = Decimal(str(v).replace(",", ""))
    except InvalidOperation:
        raise ValueError(f"{field} must be a number, not “{v}”")
    if n != n.to_integral_value() or n < 0:
        raise ValueError(f"{field} must be a whole number, not “{v}”")
    return int(n)


class Command(BaseCommand):
    help = "Add or update customers, suppliers and price-group prices from Excel."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true", help="Check the file and report, but save nothing.")

    def handle(self, path, dry_run, **options):
        try:
            wb = load_workbook(path, data_only=True)
        except PermissionError:
            raise CommandError(f"Cannot read {path}. Close it in Excel and try again.")
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")

        self.errors, report = [], []
        try:
            with transaction.atomic():
                report.append(self.customers(wb))
                report.append(self.suppliers(wb))
                report.append(self.prices(wb))
                if self.errors:
                    raise CommandError("Nothing was saved. Fix these rows and run again:\n  " + "\n  ".join(self.errors))
                if dry_run:
                    raise DryRun
        except DryRun:
            pass
        for line in report:
            if line:
                self.stdout.write(("Would: " if dry_run else "") + line)
        self.stdout.write("Dry run: nothing was saved." if dry_run else self.style.SUCCESS("Done."))

    def fail(self, sheet, n, name, e):
        self.errors.append(f"{sheet} row {n} {name}: {e}")

    def customers(self, wb):
        types = {t.value for t in Customer.Type}
        groups = {g.name.lower(): g for g in PriceGroup.objects.all()}
        added = updated = 0
        for n, r in sheet_rows(wb, "Customers"):
            name = text(r.get("Name"))
            if not name:
                continue
            try:
                ctype = text(r.get("Type"))
                if ctype not in types:
                    raise ValueError(f"Type must be one of {', '.join(sorted(types))}, not “{ctype}”")
                group_name = text(r.get("Price group"))
                if group_name and group_name.lower() not in groups:
                    raise ValueError(f"unknown price group “{group_name}”")
                values = {
                    "type": ctype,
                    "price_group": groups.get(group_name.lower()) if group_name else None,
                    "tax_no": text(r.get("Tax no.")),
                    "billing_address": text(r.get("Billing address")),
                    "delivery_address": text(r.get("Delivery address")),
                    "contact_person": text(r.get("Contact person")),
                    "phone": text(r.get("Phone")),
                    "payment_terms_days": whole(r.get("Payment terms (days)"), "Payment terms") or 0,
                    "notes": text(r.get("Notes")),
                }
                _, new = Customer.objects.update_or_create(name=name, defaults=values)
                added += new
                updated += not new
            except ValueError as e:
                self.fail("Customers", n, name, e)
        if added or updated:
            return f"customers: added {added}, updated {updated}."

    def suppliers(self, wb):
        currencies = {c.value for c in Currency}
        added = updated = 0
        for n, r in sheet_rows(wb, "Suppliers"):
            name = text(r.get("Name"))
            if not name:
                continue
            try:
                currency = text(r.get("Currency")).upper() or "MMK"
                if currency not in currencies:
                    raise ValueError(f"Currency must be one of {', '.join(sorted(currencies))}, not “{currency}”")
                values = {
                    "country": text(r.get("Country")) or "Myanmar",
                    "currency": currency,
                    "supplies": text(r.get("Supplies")),
                    "contact_person": text(r.get("Contact person")),
                    "phone": text(r.get("Phone")),
                    "email": text(r.get("Email")),
                    "address": text(r.get("Address")),
                    "payment_terms": text(r.get("Payment terms")),
                    "payment_method": text(r.get("Payment method")),
                    "notes": text(r.get("Notes")),
                }
                _, new = Supplier.objects.update_or_create(name=name, defaults=values)
                added += new
                updated += not new
            except ValueError as e:
                self.fail("Suppliers", n, name, e)
        if added or updated:
            return f"suppliers: added {added}, updated {updated}."

    def prices(self, wb):
        groups = list(PriceGroup.objects.all())
        saved = 0
        for n, r in sheet_rows(wb, "Prices"):
            code = text(r.get("Item code"))
            if not code:
                continue
            try:
                item = Item.objects.filter(code=code).first()
                if not item:
                    raise ValueError("no item with this code")
                unit = text(r.get("Unit")).lower() or "pkt"
                if unit not in ("pkt", "ctn"):
                    raise ValueError(f"Unit must be pkt or ctn, not “{unit}”")
                start = to_date(r.get("Valid from"), "Valid from")
                for group in groups:
                    amount = whole(r.get(group.name), group.name)
                    if not amount:
                        continue
                    # End the previous open price, then set this one
                    Price.objects.filter(
                        item=item, price_group=group, unit=unit, min_qty=1, valid_from__lt=start, valid_to__isnull=True
                    ).update(valid_to=start - timedelta(days=1))
                    Price.objects.update_or_create(
                        item=item, price_group=group, customer=None, unit=unit, min_qty=1, valid_from=start,
                        defaults={"price": amount, "note": text(r.get("Source"))[:200]},
                    )
                    saved += 1
            except ValueError as e:
                self.fail("Prices", n, code, e)
        if saved:
            return f"prices: saved {saved} group prices."
