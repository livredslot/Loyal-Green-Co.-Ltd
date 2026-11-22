from django.urls import path

from . import views

urlpatterns = [
    path("", views.item_list, name="item_list"),
    path("new/", views.item_create, name="item_create"),
    path("<int:pk>/", views.item_detail, name="item_detail"),
    path("<int:pk>/edit/", views.item_edit, name="item_edit"),
    path("<int:pk>/recipe/", views.recipe_edit, name="recipe_edit"),
    path("locations-machines/", views.setup_lists, name="setup_lists"),
]
