import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from accounts.models import User
from accounts.roles import DIRECTOR, PRODUCTION_LEAD, WAREHOUSE_LEAD

from .models import Category, ConversionError, Item, Location, Machine, Recipe, RecipeLine


def make_item(code="PC-07W-25", **kw):
    category, _ = Category.objects.get_or_create(name=kw.pop("category", "Paper cup"))
    defaults = {"name_en": code, "type": "FG", "stock_unit": "pkt", "pcs_per_pkt": 25, "pkt_per_ctn": 80}
    defaults.update(kw)
    return Item.objects.create(code=code, category=category, **defaults)


def user_with_role(role, username=None):
    user = User.objects.create_user(username or role.lower().replace(" ", "_"), password="x-long-password")
    user.groups.add(Group.objects.get(name=role))
    return user


class ConversionTests(TestCase):
    def test_carton_packet_piece_chain(self):
        cup = make_item()
        self.assertEqual(cup.pcs_per_ctn, 2000)
        self.assertEqual(cup.convert(1, "ctn"), 80)  # into stock unit (pkt)
        self.assertEqual(cup.convert(2000, "pcs", "ctn"), 1)
        self.assertEqual(cup.convert(3, "pkt", "pcs"), 75)

    def test_paper_fan_kg_to_pieces(self):
        fan = make_item("RM-FAN07W", type="RM", stock_unit="kg", pcs_per_pkt=None, pkt_per_ctn=None,
                        weight_per_100_g=Decimal("358"), category="Paper fan")
        # 2,000 fans weigh 7.16 kg
        self.assertEqual(fan.convert(2000, "pcs"), Decimal("7.16"))
        self.assertEqual(fan.convert(1, "ton", "kg"), 1000)
        self.assertEqual(round(fan.convert(1, "kg", "pcs")), 279)

    def test_missing_pack_size_is_an_error(self):
        roll = make_item("RM-BR145", type="RM", stock_unit="kg", pcs_per_pkt=None, pkt_per_ctn=None)
        with self.assertRaises(ConversionError):
            roll.convert(10, "pcs")


class RecipeTests(TestCase):
    def test_material_taken_from_stock_includes_waste(self):
        cup = make_item()
        fan = make_item("RM-FAN07W", type="RM", stock_unit="kg", pcs_per_pkt=None, pkt_per_ctn=None,
                        weight_per_100_g=Decimal("358"), category="Paper fan")
        recipe = Recipe.objects.create(item=cup, output_qty=1, output_unit="ctn")
        line = RecipeLine.objects.create(recipe=recipe, material=fan, quantity=2000, unit="pcs", waste_percent=2)
        # 7.16 kg + 2% = 7.3032 kg per carton
        self.assertEqual(line.stock_qty_with_waste, Decimal("7.3032"))


class SeedTests(TestCase):
    def test_locations_and_machines_seeded(self):
        self.assertEqual(set(Location.objects.values_list("code", flat=True)), {"RAW", "FG", "REPACK"})
        self.assertEqual(Machine.objects.count(), 8)
        self.assertEqual(Machine.objects.get(name="Noodle Bowl").output_per_hour, 720)

    def test_role_permissions(self):
        director = user_with_role(DIRECTOR)
        production = user_with_role(PRODUCTION_LEAD)
        warehouse = user_with_role(WAREHOUSE_LEAD)
        self.assertTrue(director.has_perm("inventory.change_item"))
        self.assertFalse(production.has_perm("inventory.change_item"))
        self.assertTrue(production.has_perm("inventory.change_recipe"))
        self.assertTrue(warehouse.has_perm("inventory.view_item"))
        self.assertFalse(warehouse.has_perm("inventory.change_recipe"))


class ItemPageTests(TestCase):
    def setUp(self):
        self.cup = make_item(name_en="7oz Paper Cup White 25's")
        make_item("PP-07W-20", name_en="7\" Paper Plate White 20's", category="Paper plate", pcs_per_pkt=20, pkt_per_ctn=100)

    def test_list_and_search(self):
        self.client.force_login(user_with_role(WAREHOUSE_LEAD))
        response = self.client.get(reverse("item_list"), {"q": "plate"})
        self.assertContains(response, "PP-07W-20")
        self.assertNotContains(response, "PC-07W-25")

    def test_detail_shows_units(self):
        self.client.force_login(user_with_role(WAREHOUSE_LEAD))
        response = self.client.get(reverse("item_detail", args=[self.cup.pk]))
        self.assertContains(response, "1 ctn = 80 pkt = 2,000 pcs")

    def test_warehouse_lead_cannot_edit(self):
        self.client.force_login(user_with_role(WAREHOUSE_LEAD))
        self.assertEqual(self.client.get(reverse("item_edit", args=[self.cup.pk])).status_code, 403)

    def test_director_edits_item_and_history_records_who(self):
        director = user_with_role(DIRECTOR)
        self.client.force_login(director)
        url = reverse("item_edit", args=[self.cup.pk])
        data = {
            "code": "PC-07W-25", "name_en": "7oz Paper Cup White 25's", "name_mm": "", "type": "FG",
            "category": self.cup.category_id, "brand": "Own", "stock_unit": "pkt", "pcs_per_pkt": 25,
            "pkt_per_ctn": 80, "weight_per_100_g": "", "barcode": "8850000000001", "lead_time_weeks": "",
            "safety_stock_weeks": "", "notes": "", "is_active": "on",
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse("item_detail", args=[self.cup.pk]))
        self.cup.refresh_from_db()
        self.assertEqual(self.cup.barcode, "8850000000001")
        self.assertEqual(self.cup.history.first().history_user, director)

    def test_production_lead_saves_recipe(self):
        fan = make_item("RM-FAN07W", type="RM", stock_unit="kg", pcs_per_pkt=None, pkt_per_ctn=None,
                        weight_per_100_g=Decimal("358"), category="Paper fan")
        self.client.force_login(user_with_role(PRODUCTION_LEAD))
        url = reverse("recipe_edit", args=[self.cup.pk])
        data = {
            "output_qty": "1", "output_unit": "ctn", "machine": "", "notes": "",
            "lines-TOTAL_FORMS": "3", "lines-INITIAL_FORMS": "0", "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
            "lines-0-material": fan.pk, "lines-0-quantity": "2000", "lines-0-unit": "pcs", "lines-0-waste_percent": "2",
            # The two empty rows, as a browser sends them
            "lines-1-waste_percent": "0", "lines-2-waste_percent": "0",
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse("item_detail", args=[self.cup.pk]))
        self.assertEqual(self.cup.recipe.lines.get().quantity, 2000)


class ImportTests(TestCase):
    HEADER = ["Code", "Name (English)", "Name (Myanmar)", "Type", "Category", "Brand", "Stock unit",
              "Pcs per pkt", "Pkt per ctn", "Pcs per ctn", "Bought in", "Weight of 100 pcs (g)", "Pcs per kg",
              "Quoted price per pkt (MMK)", "Source", "Notes", "Question", "Check", "Correction / comment"]

    def write_file(self, rows):
        wb = Workbook()
        ws = wb.active
        ws.title = "Items"
        ws.append(self.HEADER)
        for r in rows:
            ws.append(r)
        path = Path(tempfile.mkdtemp()) / "items.xlsx"
        wb.save(path)
        return path

    def row(self, code, name, typ="FG", cat="Paper cup", unit="pkt", pcs=25, pkt=80, w100=None, check="OK", comment=None):
        return [code, name, None, typ, cat, "Own", unit, pcs, pkt, None, None, w100, None, None, None, None, None, check, comment]

    def test_import_adds_updates_and_skips(self):
        make_item("PC-07W-25", name_en="Old name")
        path = self.write_file([
            self.row("PC-07W-25", "7oz Paper Cup White 25's"),
            self.row("RM-FAN07W", "7oz Cup Fan", typ="RM", cat="Paper fan", unit="kg", pcs=None, pkt=None, w100=358),
            self.row("XX-OLD", "Discontinued", check="Delete"),
            self.row("PP-07C-20", "7\" Plate Colour", check="Change", comment="price is wrong"),
        ])
        out = StringIO()
        call_command("import_items", str(path), stdout=out)
        self.assertEqual(Item.objects.get(code="PC-07W-25").name_en, "7oz Paper Cup White 25's")
        self.assertEqual(Item.objects.get(code="RM-FAN07W").weight_per_100_g, 358)
        self.assertFalse(Item.objects.filter(code="XX-OLD").exists())
        self.assertIn("Added 2, updated 1, skipped 1", out.getvalue())
        self.assertIn("price is wrong", out.getvalue())

    def test_dry_run_saves_nothing(self):
        path = self.write_file([self.row("PC-07W-25", "Cup")])
        call_command("import_items", str(path), "--dry-run", stdout=StringIO())
        self.assertFalse(Item.objects.exists())

    def test_bad_row_saves_nothing(self):
        path = self.write_file([self.row("PC-07W-25", "Cup"), self.row("BAD", "Bad", typ="ZZ")])
        with self.assertRaisesMessage(CommandError, "row 3 BAD"):
            call_command("import_items", str(path), stdout=StringIO())
        self.assertFalse(Item.objects.exists())
