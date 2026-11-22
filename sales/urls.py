from django.urls import path

from . import views

urlpatterns = [
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/new/", views.customer_create, name="customer_create"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("customers/<int:pk>/prices/new/", views.special_price_add, name="special_price_add"),
    path("prices/", views.price_list, name="price_list"),
    path("prices/<int:pk>/edit/", views.price_group_edit, name="price_group_edit"),
]
