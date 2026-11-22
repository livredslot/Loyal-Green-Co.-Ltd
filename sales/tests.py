import tempfile
from datetime import date
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from accounts.models import User
from accounts.roles import ACCOUNTANT, DIRECTOR, SALES_MANAGER, WAREHOUSE_LEAD
from inventory.models import Category, Item
from purchasing.models import Supplier

from .models import Customer, Price, PriceGroup
from .pricing import unit_price


def make_item(code="PC-07W-25", pcs=25, pkt=80):
    category, _ = Category.objects.get_or_create(name="Paper cup")
    return Item.objects.create(code=code, name_en=code, type="FG", category=category, stock_unit="pkt", pcs_per_pkt=pcs, pkt_per_ctn=pkt)


def user_with_role(role):
    user = User.objects.create_user(role.lower().replace(" ", "_"), password="x-long-password")
    user.groups.add(Group.objects.get(name=role))
    return user


class PricingTests(TestCase):
    def setUp(self):
        self.cup = make_item()
        self.supermarket = PriceGroup.objects.get(name="Supermarket")
        self.city_mart = Customer.objects.create(name="City Mart", type="Supermarket", price_group=self.supermarket)
        Price.objects.create(item=self.cup, price_group=self.supermarket, price=6000, valid_from=date(2026, 10, 5))

    def test_group_price_and_carton_from_packets(self):
        self.assertEqual(unit_price(self.cup, self.city_mart, unit="pkt", on=date(2026, 11, 1)), 6000)
        self.assertEqual(unit_price(self.cup, self.city_mart, unit="ctn", on=date(2026, 11, 1)), 6000 * 80)

    def test_no_price_before_it_starts(self):
        self.assertIsNone(unit_price(self.cup, self.city_mart, on=date(2026, 10, 1)))

    def test_special_price_beats_group_price(self):
        Price.objects.create(item=self.cup, customer=self.city_mart, price=5800, valid_from=date(2026, 11, 1))
        self.assertEqual(unit_price(self.cup, self.city_mart, on=date(2026, 11, 2)), 5800)
        other = Customer.objects.create(name="Capital", type="Supermarket", price_group=self.supermarket)
        self.assertEqual(unit_price(self.cup, other, on=date(2026, 11, 2)), 6000)

    def test_quantity_break(self):
        Price.objects.create(item=self.cup, price_group=self.supermarket, price=5700, min_qty=80, valid_from=date(2026, 10, 5))
        self.assertEqual(unit_price(self.cup, self.city_mart, qty=10, on=date(2026, 11, 1)), 6000)
        self.assertEqual(unit_price(self.cup, self.city_mart, qty=80, on=date(2026, 11, 1)), 5700)

    def test_customer_without_group_has_no_price(self):
        company = Customer.objects.create(name="Samsung", type="Company")
        self.assertIsNone(unit_price(self.cup, company))


class PermissionTests(TestCase):
    def test_roles(self):
        director, sales, accountant, warehouse = (user_with_role(r) for r in (DIRECTOR, SALES_MANAGER, ACCOUNTANT, WAREHOUSE_LEAD))
        self.assertTrue(director.has_perm("sales.change_price"))
        self.assertFalse(sales.has_perm("sales.change_price"))
        self.assertTrue(sales.has_perm("sales.add_customer"))
        self.assertTrue(accountant.has_perm("purchasing.change_supplier"))
        self.assertFalse(warehouse.has_perm("sales.view_price"))
        self.assertTrue(warehouse.has_perm("sales.view_customer"))


class CustomerPageTests(TestCase):
    def form_data(self, **kw):
        data = {"name": "Bazaar", "type": "Supermarket", "price_group": PriceGroup.objects.get(name="Supermarket").pk,
                "tax_no": "", "billing_address": "", "delivery_address": "", "contact_person": "", "phone": "",
                "email": "", "payment_terms_days": "30", "credit_limit": "5000000", "salesperson": "", "notes": "", "is_active": "on"}
        data.update(kw)
        return data

    def test_sales_manager_cannot_set_terms_or_credit_limit(self):
        self.client.force_login(user_with_role(SALES_MANAGER))
        response = self.client.post(reverse("customer_create"), self.form_data())
        customer = Customer.objects.get(name="Bazaar")
        self.assertRedirects(response, customer.get_absolute_url())
        self.assertEqual(customer.payment_terms_days, 0)
        self.assertIsNone(customer.credit_limit)

    def test_director_sets_terms_and_credit_limit(self):
        self.client.force_login(user_with_role(DIRECTOR))
        self.client.post(reverse("customer_create"), self.form_data())
        customer = Customer.objects.get(name="Bazaar")
        self.assertEqual((customer.payment_terms_days, customer.credit_limit), (30, 5000000))

    def test_warehouse_lead_sees_customers_but_not_prices(self):
        self.client.force_login(user_with_role(WAREHOUSE_LEAD))
        self.assertEqual(self.client.get(reverse("customer_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("price_list")).status_code, 403)


class PriceEditTests(TestCase):
    def test_changing_a_price_keeps_the_old_one_as_history(self):
        cup = make_item()
        group = PriceGroup.objects.get(name="Supermarket")
        old = Price.objects.create(item=cup, price_group=group, price=6000, valid_from=date(2026, 10, 5))
        self.client.force_login(user_with_role(DIRECTOR))
        response = self.client.post(reverse("price_group_edit", args=[group.pk]), {"valid_from": "2026-12-01", f"price_{cup.pk}": "6300"})
        self.assertRedirects(response, reverse("price_list"))
        old.refresh_from_db()
        self.assertEqual(old.valid_to, date(2026, 11, 30))
        self.assertEqual(unit_price(cup, price_group=group, on=date(2026, 12, 1)), 6300)
        self.assertEqual(unit_price(cup, price_group=group, on=date(2026, 11, 15)), 6000)

    def test_price_list_shows_current_prices(self):
        cup = make_item()
        Price.objects.create(item=cup, price_group=PriceGroup.objects.get(name="Wholesale"), price=5500, valid_from=date(2026, 10, 5))
        self.client.force_login(user_with_role(SALES_MANAGER))
        self.assertContains(self.client.get(reverse("price_list")), "5,500")


class ImportTests(TestCase):
    def write_file(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Customers"
        ws.append(["Name", "Type", "Price group", "Tax no.", "Billing address", "Delivery address", "Contact person", "Phone", "Payment terms (days)", "Notes", "Check"])
        ws.append(["City Mart", "Supermarket", "Supermarket", "113516550", "Sanchaung", "Dagon Seikkan", "Maung Maung Oo", "09400412235", 60, None, "OK"])
        ws.append(["ARO", "Wholesale", "Wholesale", None, None, None, None, None, 0, None, "Delete"])
        ws = wb.create_sheet("Suppliers")
        ws.append(["Name", "Country", "Currency", "Supplies", "Check"])
        ws.append(["Susan", "China", "USD", "Paper fans", "OK"])
        ws = wb.create_sheet("Prices")
        ws.append(["Item code", "Item name", "Unit", "Supermarket", "Wholesale", "Retail shop", "Hotel / restaurant", "Valid from", "Source", "Check"])
        ws.append(["PC-07W-25", "Cup", "pkt", 6000, 6000, None, 6100, date(2026, 10, 5), "Quotation", "OK"])
        path = Path(tempfile.mkdtemp()) / "data.xlsx"
        wb.save(path)
        return path

    def test_import(self):
        make_item()
        out = StringIO()
        call_command("import_sales_data", str(self.write_file()), stdout=out)
        city_mart = Customer.objects.get(name="City Mart")
        self.assertEqual((city_mart.price_group.name, city_mart.payment_terms_days), ("Supermarket", 60))
        self.assertFalse(Customer.objects.filter(name="ARO").exists())
        self.assertEqual(Supplier.objects.get(name="Susan").currency, "USD")
        self.assertEqual(Price.objects.count(), 3)
        self.assertEqual(unit_price(Item.objects.get(code="PC-07W-25"), city_mart), 6000)
        self.assertIn("prices: saved 3", out.getvalue())

    def test_unknown_item_saves_nothing(self):
        with self.assertRaisesMessage(CommandError, "Prices row 2 PC-07W-25: no item"):
            call_command("import_sales_data", str(self.write_file()), stdout=StringIO())
        self.assertFalse(Customer.objects.exists())
