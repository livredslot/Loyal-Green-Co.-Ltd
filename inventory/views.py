from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ItemForm, RecipeForm, RecipeLineFormSet
from .models import Category, ConversionError, Item, Location, Machine, Recipe


@login_required
@permission_required("inventory.view_item", raise_exception=True)
def item_list(request):
    items = Item.objects.select_related("category")
    q = request.GET.get("q", "").strip()
    item_type = request.GET.get("type", "")
    category = request.GET.get("category", "")
    show_inactive = request.GET.get("inactive") == "1"
    if q:
        items = items.filter(Q(code__icontains=q) | Q(name_en__icontains=q) | Q(name_mm__icontains=q) | Q(barcode=q))
    if item_type:
        items = items.filter(type=item_type)
    if category:
        items = items.filter(category_id=category)
    if not show_inactive:
        items = items.filter(is_active=True)
    return render(request, "inventory/item_list.html", {
        "items": items,
        "types": Item.Type.choices,
        "categories": Category.objects.all(),
        "q": q, "item_type": item_type, "category": category, "show_inactive": show_inactive,
    })


@login_required
@permission_required("inventory.view_item", raise_exception=True)
def item_detail(request, pk):
    item = get_object_or_404(Item.objects.select_related("category"), pk=pk)
    recipe = getattr(item, "recipe", None)
    lines = []
    if recipe:
        for line in recipe.lines.select_related("material"):
            try:
                stock_qty = line.stock_qty_with_waste
            except ConversionError:
                stock_qty = None
            lines.append((line, stock_qty))
    return render(request, "inventory/item_detail.html", {
        "item": item,
        "recipe": recipe,
        "lines": lines,
        "used_in": item.used_in.select_related("recipe__item"),
        "history": item.history.select_related("history_user")[:10],
    })


@login_required
@permission_required("inventory.add_item", raise_exception=True)
def item_create(request):
    form = ItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"Item {item.code} added.")
        return redirect(item)
    return render(request, "inventory/item_form.html", {"form": form, "title": "New item"})


@login_required
@permission_required("inventory.change_item", raise_exception=True)
def item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk)
    form = ItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Item {item.code} saved.")
        return redirect(item)
    return render(request, "inventory/item_form.html", {"form": form, "item": item, "title": f"Edit {item.code}"})


@login_required
@permission_required("inventory.change_recipe", raise_exception=True)
def recipe_edit(request, pk):
    item = get_object_or_404(Item, pk=pk, type__in=["FG", "TG"])
    recipe = getattr(item, "recipe", None) or Recipe(item=item)
    form = RecipeForm(request.POST or None, instance=recipe)
    formset = RecipeLineFormSet(request.POST or None, instance=recipe)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        recipe = form.save()
        formset.instance = recipe
        formset.save()
        messages.success(request, f"Recipe for {item.code} saved.")
        return redirect(item)
    return render(request, "inventory/recipe_form.html", {"item": item, "form": form, "formset": formset})


@login_required
@permission_required("inventory.view_machine", raise_exception=True)
def setup_lists(request):
    return render(request, "inventory/setup_lists.html", {
        "locations": Location.objects.all(),
        "machines": Machine.objects.all(),
        "categories": Category.objects.all(),
    })
