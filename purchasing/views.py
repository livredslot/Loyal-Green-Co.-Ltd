from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import Supplier


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "country", "currency", "supplies", "contact_person", "phone", "email", "address",
                  "payment_terms", "payment_method", "notes", "is_active"]
        widgets = {"address": forms.Textarea(attrs={"rows": 2}), "notes": forms.Textarea(attrs={"rows": 2})}


@login_required
@permission_required("purchasing.view_supplier", raise_exception=True)
def supplier_list(request):
    suppliers = Supplier.objects.all()
    q = request.GET.get("q", "").strip()
    if q:
        suppliers = suppliers.filter(Q(name__icontains=q) | Q(supplies__icontains=q) | Q(contact_person__icontains=q))
    if request.GET.get("inactive") != "1":
        suppliers = suppliers.filter(is_active=True)
    return render(request, "purchasing/supplier_list.html", {"suppliers": suppliers, "q": q, "show_inactive": request.GET.get("inactive") == "1"})


@login_required
@permission_required("purchasing.view_supplier", raise_exception=True)
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    return render(request, "purchasing/supplier_detail.html", {
        "supplier": supplier, "history": supplier.history.select_related("history_user")[:10],
    })


def _save(request, supplier=None):
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == "POST" and form.is_valid():
        supplier = form.save()
        messages.success(request, f"{supplier.name} saved.")
        return redirect(supplier)
    title = f"Edit {supplier.name}" if supplier else "New supplier"
    return render(request, "purchasing/supplier_form.html", {"form": form, "supplier": supplier, "title": title})


@login_required
@permission_required("purchasing.add_supplier", raise_exception=True)
def supplier_create(request):
    return _save(request)


@login_required
@permission_required("purchasing.change_supplier", raise_exception=True)
def supplier_edit(request, pk):
    return _save(request, get_object_or_404(Supplier, pk=pk))
