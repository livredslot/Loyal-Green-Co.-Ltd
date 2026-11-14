from django.contrib.auth.models import AbstractUser
from django.db import models

from .roles import ROLES


class User(AbstractUser):
    """A person who logs in. Their role is the Django group they belong to."""

    phone = models.CharField(max_length=30, blank=True)

    @property
    def role(self):
        """The user's role name (Director, Sales Manager, ...), or '' if none."""
        names = set(self.groups.values_list("name", flat=True))
        return next((r for r in ROLES if r in names), "")
