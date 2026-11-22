"""
Load the item list from the Excel file the team confirmed ("Items" sheet).

    python manage.py import_items "Item List.xlsx" --dry-run
    python manage.py import_items "Item List.xlsx"

Rows are matched on Code: new codes are added, existing ones updated. Rows marked
Delete in the Check column are skipped. Rows marked Change or Not sure that carry a
comment are listed, because the comment itself is not applied.
"""

from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from inventory.models import Category, Item, Unit

COLUMNS = {
    "code": "Code",
    "name_en": "Name (English)",
    "name_mm": "Name (Myanmar)",
    "type": "Type",
    "category": "Category",
    "brand": "Brand",
    "stock_unit": "Stock unit",
    "pcs_per_pkt": "Pcs per pkt",
    "pkt_per_ctn": "Pkt per ctn",
    "weight_per_100_g": "Weight of 100 pcs (g)",
    "barcode": "Barcode",
    "notes": "Notes",
    "check": "Check",
    "comment": "Correction / comment",
}
REQUIRED = ["code", "name_en", "type", "category", "stock_unit"]


class DryRun(Exception):
    pass


def text(v):
    return "" if v is None else str(v).strip()


def whole_number(v, field):
    if v in (None, ""):
        return None
    try:
        n = Decimal(str(v))
    except InvalidOperation:
        raise ValueError(f"{field} must be a number, not “{v}”")
    if n != n.to_integral_value() or n <= 0:
        raise ValueError(f"{field} must be a whole number above 0, not “{v}”")
    return int(n)


def decimal(v, field):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except InvalidOperation:
        raise ValueError(f"{field} must be a number, not “{v}”")


class Command(BaseCommand):
    help = "Add or update items from the confirmed Excel item list."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--sheet", default="Items")
        parser.add_argument("--dry-run", action="store_true", help="Check the file and report, but save nothing.")

    def handle(self, path, sheet, dry_run, **options):
        try:
            ws = load_workbook(path, data_only=True)[sheet]
        except PermissionError:
            raise CommandError(f"Cannot read {path}. Close it in Excel and try again.")
        except (FileNotFoundError, KeyError) as e:
            raise CommandError(f"Cannot open sheet “{sheet}” in {path}: {e}")

        rows = ws.iter_rows(values_only=True)
        header = [text(h) for h in next(rows)]
        col = {key: header.index(name) for key, name in COLUMNS.items() if name in header}
        missing = [COLUMNS[k] for k in REQUIRED if k not in col]
        if missing:
            raise CommandError(f"Missing columns: {', '.join(missing)}")

        types = {t.value for t in Item.Type}
        units = {u.value for u in Unit}
        created = updated = skipped = 0
        errors, to_review = [], []

        try:
            with transaction.atomic():
                for n, row in enumerate(rows, start=2):
                    get = lambda key: row[col[key]] if key in col and col[key] < len(row) else None  # noqa: E731
                    code = text(get("code"))
                    if not code:
                        continue
                    check = text(get("check")).lower()
                    if check == "delete":
                        skipped += 1
                        continue
                    if check in ("change", "not sure") and text(get("comment")):
                        to_review.append(f"row {n} {code}: {text(get('comment'))}")
                    try:
                        item_type = text(get("type")).upper()
                        stock_unit = text(get("stock_unit")).lower()
                        if item_type not in types:
                            raise ValueError(f"Type must be one of {', '.join(sorted(types))}, not “{item_type}”")
                        if stock_unit not in units:
                            raise ValueError(f"Stock unit must be one of {', '.join(units)}, not “{stock_unit}”")
                        name_en = text(get("name_en"))
                        if not name_en:
                            raise ValueError("Name (English) is empty")
                        category_name = text(get("category")) or "Other"
                        category, _ = Category.objects.get_or_create(name__iexact=category_name, defaults={"name": category_name})
                        values = {
                            "name_en": name_en,
                            "type": item_type,
                            "category": category,
                            "brand": text(get("brand")),
                            "stock_unit": stock_unit,
                            "pcs_per_pkt": whole_number(get("pcs_per_pkt"), "Pcs per pkt"),
                            "pkt_per_ctn": whole_number(get("pkt_per_ctn"), "Pkt per ctn"),
                            "weight_per_100_g": decimal(get("weight_per_100_g"), "Weight of 100 pcs"),
                        }
                        # Optional columns only overwrite when the file has them
                        for key in ("name_mm", "barcode", "notes"):
                            if key in col:
                                values[key] = text(get(key))
                        _, is_new = Item.objects.update_or_create(code=code, defaults=values)
                        created += is_new
                        updated += not is_new
                    except ValueError as e:
                        errors.append(f"row {n} {code}: {e}")

                if errors:
                    raise CommandError("Nothing was saved. Fix these rows and run again:\n  " + "\n  ".join(errors))
                if dry_run:
                    raise DryRun
        except DryRun:
            pass

        verb = "Would add" if dry_run else "Added"
        self.stdout.write(f"{verb} {created}, {'would update' if dry_run else 'updated'} {updated}, skipped {skipped} (Delete).")
        if to_review:
            self.stdout.write(self.style.WARNING("Check these comments by hand:\n  " + "\n  ".join(to_review)))
        if dry_run:
            self.stdout.write("Dry run: nothing was saved.")
        else:
            self.stdout.write(self.style.SUCCESS("Done."))
