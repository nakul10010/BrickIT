from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import DecimalField, ExpressionWrapper, F
from datetime import date
from .forms import SalesForm
from .models import Customer, Sales
from core.models import BrickType

@login_required
def customer_list(request):
    customers = Customer.objects.all()

    context = {
        "customers": customers,
    }
    return render(
        request,
        "Sales/customer_list.html",
        context
    )
@login_required
def customer_detail(request, customer_id):
    customer = get_object_or_404(
        Customer,
        pk=customer_id
    )

    customer_sales = Sales.objects.filter(
        customer=customer
    ).order_by("-date")

    context = {
        "customer": customer,
        "customer_sales": customer_sales,
    }

    return render(
        request,
        "Sales/customer_detail.html",
        context
    )

    customer_sales = Sales.objects.filter(
        customer=customer
    ).order_by("-date")

    context = {
        "customer": customer,
        "customer_sales": customer_sales,
    }

    return render(
        request,
        "Sales/customer_detail.html",
        context
    )

    return render(
        request,
        "Sales/customer_list.html",
        context
    )

@login_required
def add_sale(request):
    if request.method == "POST":
        form = SalesForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("home")

    else:
        form = SalesForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "Sales/add_sale.html",
        context
    )
@login_required
def sales_list(request):
    all_sales = Sales.objects.select_related("customer", "brick_type").annotate(
        sort_amount=ExpressionWrapper(
            F("quantity") * F("price_per_brick"),
            output_field=DecimalField(max_digits=16, decimal_places=2),
        )
    )

    selected_year = request.GET.get("year", "")
    if selected_year:
        try:
            selected_year = int(selected_year)
            if selected_year < 1 or selected_year > 9999:
                raise ValueError
            all_sales = all_sales.filter(date__year=selected_year)
        except (TypeError, ValueError):
            selected_year = ""

    selected_month = request.GET.get("month", "")
    if selected_month:
        try:
            selected_date = date.fromisoformat(f"{selected_month}-01")
            all_sales = all_sales.filter(
                date__year=selected_date.year,
                date__month=selected_date.month,
            )
        except ValueError:
            selected_month = ""

    selected_brick_type = request.GET.get("brick_type", "")
    if selected_brick_type:
        try:
            all_sales = all_sales.filter(brick_type_id=int(selected_brick_type))
        except ValueError:
            selected_brick_type = ""

    sort_options = {
        "amount_asc": "sort_amount",
        "amount_desc": "-sort_amount",
        "quantity_asc": "quantity",
        "quantity_desc": "-quantity",
    }
    selected_sort = request.GET.get("sort", "date_desc")
    all_sales = all_sales.order_by(sort_options.get(selected_sort, "-date"), "-date")

    total_quantity = 0
    total_amount = 0
    total_paid = 0
    total_due = 0

    for sale in all_sales:
        total_quantity = total_quantity + sale.quantity
        total_amount = total_amount + sale.total_amount()
        total_paid = total_paid + sale.amount_paid
        total_due = total_due + sale.amount_due()

    context = {
        "all_sales": all_sales,
        "total_quantity": total_quantity,
        "total_amount": total_amount,
        "total_paid": total_paid,
        "total_due": total_due,
        "brick_types": BrickType.objects.all(),
        "sales_years": Sales.objects.dates("date", "year", order="DESC"),
        "selected_year": selected_year,
        "selected_month": selected_month,
        "selected_brick_type": selected_brick_type,
        "selected_sort": selected_sort if selected_sort in (*sort_options, "date_desc") else "date_desc",
    }

    return render(
        request,
        "Sales/sales_list.html",
        context
    )


@login_required
def delivery_list(request):
    deliveries = Sales.objects.select_related("customer", "brick_type").order_by(
        "delivery_date", "delivery_time", "date"
    )
    context = {
        "pending_deliveries": deliveries.filter(is_delivered=False),
        "completed_deliveries": deliveries.filter(is_delivered=True),
    }
    return render(request, "Sales/delivery_list.html", context)


@require_POST
@login_required
def mark_delivered(request, sale_id):
    sale = get_object_or_404(Sales, pk=sale_id)
    sale.is_delivered = True
    sale.save(update_fields=["is_delivered"])
    return redirect("delivery_list")


@require_POST
@login_required
def mark_not_delivered(request, sale_id):
    sale = get_object_or_404(Sales, pk=sale_id)
    sale.is_delivered = False
    sale.save(update_fields=["is_delivered"])
    return redirect("delivery_list")
