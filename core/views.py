from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

# Modules of version 1, in build order (design document, "Plan"). The URL name
# is filled in once a module is built.
MODULES = [
    ("Items and units", "Item list, units, recipes, locations", "item_list"),
    ("Customers, suppliers and prices", "Customer terms, supplier list, price groups and special prices", "customer_list"),
    ("Purchasing and stock", "Purchase orders, goods received, import costs, reorder alerts", None),
    ("Production and repacking", "Daily production per machine, repacking", None),
    ("Sales", "Orders, delivery orders, invoices, payments, credit alerts", None),
    ("Reports", "Costing, gross profit, stock value, dashboard figures", None),
]


@login_required
def dashboard(request):
    modules = [(name, description, reverse(url) if url else None) for name, description, url in MODULES]
    return render(request, "core/dashboard.html", {"modules": modules})
