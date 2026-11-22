from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from inventory.models import Category, Item

from .forms import CustomerForm, GroupPricesForm, SpecialPriceForm
from .models import Customer, Price, PriceGroup
from .pricing import current_group_prices


@login_required
@permission_required("sales.view_customer", raise_exception=True)
def customer_list(request):
    customers = Customer.objects.select_related("price_group", "salesperson")
    q = request.GET.get("q", "").strip()
    customer_type = request.GET.get("type", "")
    group = request.GET.get("group", "")
    show_inactive = request.GET.get("inactive") == "1"
    if q:
        customers = customers.filter(Q(name__icontains=q) | Q(contact_person__icontains=q) | Q(phone__icontains=q) | Q(tax_no=q))
    if customer_type:
        customers = customers.filter(type=customer_type)
    if group == "none":
        customers = customers.filter(price_group__isnull=True)
    elif group:
        customers = customers.filter(price_group_id=group)
    if not show_inactive:
        customers = customers.filter(is_active=True)
    return render(request, "sales/customer_list.html", {
        "customers": customers, "types": Customer.Type.choices, "groups": PriceGroup.objects.all(),
        "q": q, "customer_type": customer_type, "group": group, "show_inactive": show_inactive,
    })


@login_required
@permission_required("sales.view_customer", raise_exception=True)
def customer_detail(request, pk):
    customer = get_object_or_404(Customer.objects.select_related("price_group", "salesperson"), pk=pk)
    special_prices = None
    if request.user.has_perm("sales.view_price"):
        special_prices = customer.special_prices.select_related("item").order_by("item__code", "-valid_from")
    return render(request, "sales/customer_detail.html", {
        "customer": customer,
        "special_prices": special_prices,
        "history": customer.history.select_related("history_user")[:10],
    })


def _save_customer(request, customer=None):
    form = CustomerForm(request.POST or None, instance=customer, user=request.user)
    if request.method == "POST" and form.is_valid():
        customer = form.save()
        messages.success(request, f"{customer.name} saved.")
        return redirect(customer)
    title = f"Edit {customer.name}" if customer else "New customer"
    return render(request, "sales/customer_form.html", {"form": form, "customer": customer, "title": title})


@login_required
@permission_required("sales.add_customer", raise_exception=True)
def customer_create(request):
    return _save_customer(request)


@login_required
@permission_required("sales.change_customer", raise_exception=True)
def customer_edit(request, pk):
    return _save_customer(request, get_object_or_404(Customer, pk=pk))


@login_required
@permission_required("sales.add_price", raise_exception=True)
def special_price_add(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = SpecialPriceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        price = form.save(commit=False)
        price.customer = customer
        price.save()
        messages.success(request, f"Special price for {price.item.code} added.")
        return redirect(customer)
    return render(request, "sales/special_price_form.html", {"form": form, "customer": customer})


def _sellable_items(category=None):
    items = Item.objects.filter(is_active=True, type__in=["FG", "TG"]).select_related("category")
    if category:
        items = items.filter(category_id=category)
    return list(items.order_by("category__name", "code"))


@login_required
@permission_required("sales.view_price", raise_exception=True)
def price_list(request):
    category = request.GET.get("category", "")
    items = _sellable_items(category)
    groups = list(PriceGroup.objects.all())
    current = current_group_prices(items, groups)
    rows = [(item, [current.get((item.pk, g.pk)) for g in groups]) for item in items]
    return render(request, "sales/price_list.html", {
        "rows": rows, "groups": groups, "categories": Category.objects.filter(items__type__in=["FG", "TG"]).distinct(),
        "category": category, "missing": sum(1 for _, prices in rows if not any(prices)),
    })


@login_required
@permission_required("sales.change_price", raise_exception=True)
def price_group_edit(request, pk):
    group = get_object_or_404(PriceGroup, pk=pk)
    category = request.GET.get("category", "")
    items = _sellable_items(category)
    current = {item_id: p for (item_id, _), p in current_group_prices(items, [group]).items()}
    form = GroupPricesForm(request.POST or None, items=items, current=current)
    if request.method == "POST" and form.is_valid():
        start = form.cleaned_data["valid_from"]
        changed = 0
        with transaction.atomic():
            for item in items:
                new = form.cleaned_data.get(f"price_{item.pk}")
                old = current.get(item.pk)
                if new is None or (old and old.price == new):
                    continue
                if old and old.valid_from >= start:
                    # Same start date: correct the price instead of adding history
                    old.price = new
                    old.save()
                else:
                    if old:
                        old.valid_to = start - timedelta(days=1)
                        old.save()
                    Price.objects.create(item=item, price_group=group, unit="pkt", price=new, valid_from=start)
                changed += 1
        messages.success(request, f"{changed} price{'s' if changed != 1 else ''} saved for {group}.")
        return redirect("price_list")
    return render(request, "sales/price_group_form.html", {
        "group": group, "form": form, "category": category,
        "categories": Category.objects.filter(items__type__in=["FG", "TG"]).distinct(),
    })
