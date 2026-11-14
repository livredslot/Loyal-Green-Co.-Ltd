from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# Modules of version 1, in build order (design document, "Plan"). Each one gets
# a real link here once it is built.
MODULES = [
    ("Items and units", "Item list, units, recipes, locations"),
    ("Purchasing and stock", "Purchase orders, goods received, import costs, reorder alerts"),
    ("Production and repacking", "Daily production per machine, repacking"),
    ("Sales", "Orders, delivery orders, invoices, payments, credit alerts"),
    ("Reports", "Costing, gross profit, stock value, dashboard figures"),
]


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html", {"modules": MODULES})
