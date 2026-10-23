from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.home,
        name="home"
    ),

    path(
        "production/add/",
        views.add_production,
        name="add_production"
    ),
    path("analytics/", views.analytics, name="analytics"),
    path("expenses/add/", views.add_expense, name="add_expense"),
    path("expenses/<int:expense_id>/edit/", views.edit_expense, name="edit_expense"),
    path("expenses/<int:expense_id>/delete/", views.delete_expense, name="delete_expense"),
]
