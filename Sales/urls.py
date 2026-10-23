from django.urls import path

from . import views


urlpatterns = [
    path(
        "customers/",
        views.customer_list,
        name="customer_list"
    ),

    path(
        "customers/<int:customer_id>/",
        views.customer_detail,
        name="customer_detail"
    ),
        path(
        "sales/add/",
        views.add_sale,
        name="add_sale"
    ),
    path(
    "sales/",
    views.sales_list,
    name="sales_list"
    ),
    path("deliveries/", views.delivery_list, name="delivery_list"),
    path("deliveries/<int:sale_id>/delivered/", views.mark_delivered, name="mark_delivered"),
    path("deliveries/<int:sale_id>/not-delivered/", views.mark_not_delivered, name="mark_not_delivered"),
]
