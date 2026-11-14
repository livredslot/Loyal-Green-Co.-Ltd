from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.roles import DIRECTOR, ROLES, WAREHOUSE_LEAD

from .models import CompanyProfile


class RolesTests(TestCase):
    def test_all_five_roles_exist(self):
        self.assertEqual(set(Group.objects.values_list("name", flat=True)), set(ROLES))

    def test_director_can_see_costs_and_approve(self):
        user = User.objects.create_user("director", password="x-long-password")
        user.groups.add(Group.objects.get(name=DIRECTOR))
        self.assertTrue(user.has_perm("core.view_costs"))
        self.assertTrue(user.has_perm("core.approve_actions"))
        self.assertEqual(user.role, DIRECTOR)

    def test_warehouse_lead_cannot_see_costs(self):
        user = User.objects.create_user("warehouse", password="x-long-password")
        user.groups.add(Group.objects.get(name=WAREHOUSE_LEAD))
        self.assertFalse(user.has_perm("core.view_costs"))
        self.assertFalse(user.has_perm("core.approve_actions"))


class CompanyProfileTests(TestCase):
    def test_only_one_profile_exists(self):
        CompanyProfile(name_en="Another").save()
        self.assertEqual(CompanyProfile.objects.count(), 1)
        self.assertEqual(CompanyProfile.load().name_en, "Another")

    def test_tax_rate_defaults_to_five_percent(self):
        self.assertEqual(CompanyProfile.load().commercial_tax_rate, 5)

    def test_changes_are_kept_in_history(self):
        profile = CompanyProfile.load()
        profile.phone = "09 123 456"
        profile.save()
        self.assertEqual(profile.history.first().phone, "09 123 456")


class PageTests(TestCase):
    def test_dashboard_needs_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next=/")

    def test_login_then_dashboard(self):
        User.objects.create_user("sales", password="x-long-password")
        response = self.client.post(reverse("login"), {"username": "sales", "password": "x-long-password"}, follow=True)
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Loyal Green Co., Ltd")
