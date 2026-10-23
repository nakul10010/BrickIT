from datetime import date
from decimal import Decimal
from calendar import month_name

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import BrickType, Expense, Inventory, Production
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncMonth
from Sales.models import Sales
from .forms import ExpenseForm, ProductionForm

@login_required
def home(request):
    brick_types = BrickType.objects.all()
    inventory = Inventory.objects.all()
    today = timezone.localdate()
    today_production = Production.objects.filter(date=today).aggregate(total=Sum('quantity'))['total'] or 0
    today_sales = Sales.objects.filter(date=today).aggregate(total=Sum("quantity"))["total"] or 0
    today_sales_amount = 0

    today_sales_records = Sales.objects.filter(date=today)

    for sale in today_sales_records:
        today_sales_amount = (
        today_sales_amount + sale.total_amount()
        )
    pending_deliveries = Sales.objects.filter(
    is_delivered=False
    ).count()
    total_due = 0

    all_sales = Sales.objects.all()
    recent_sales = Sales.objects.order_by("-date")[:5]

    for sale in all_sales:
        total_due = total_due + sale.amount_due()
    context = {
        "business_name": "BrickIT",
        "brick_types": brick_types,
        "inventory": inventory,
        "today_production": today_production,
        "today_sales": today_sales,
        "today_sales_amount": today_sales_amount,
        "pending_deliveries": pending_deliveries,
        "total_due": total_due,
        "recent_sales": recent_sales
    }

    return render(request, "core/home.html", context)


@login_required
def analytics(request):
    current_year = timezone.localdate().year
    available_years = list(Sales.objects.dates("date", "year", order="DESC"))
    available_expense_years = Expense.objects.dates("date", "year", order="DESC")
    years = sorted(
        {current_year, *(item.year for item in available_years), *(item.year for item in available_expense_years)},
        reverse=True,
    )

    try:
        selected_year = int(request.GET.get("year", current_year))
        if selected_year < 1 or selected_year > 9999:
            raise ValueError
    except (TypeError, ValueError):
        selected_year = current_year

    year_sales = Sales.objects.filter(date__year=selected_year)
    year_expenses = Expense.objects.filter(date__year=selected_year)
    selected_customer_month = request.GET.get("customer_month", "")
    customer_month_number = None
    if selected_customer_month:
        try:
            customer_month_number = int(selected_customer_month)
            if customer_month_number < 1 or customer_month_number > 12:
                raise ValueError
        except (TypeError, ValueError):
            selected_customer_month = ""
            customer_month_number = None

    customer_sales = year_sales
    if customer_month_number:
        customer_sales = customer_sales.filter(date__month=customer_month_number)
    sales_value_expression = ExpressionWrapper(
        F("quantity") * F("price_per_brick"),
        output_field=DecimalField(max_digits=20, decimal_places=2),
    )
    totals = year_sales.aggregate(
        quantity_total=Sum("quantity"),
        sales_value=Sum(sales_value_expression),
        amount_received=Sum("amount_paid"),
    )
    production_total = Production.objects.filter(date__year=selected_year).aggregate(
        quantity=Sum("quantity")
    )["quantity"] or 0

    cost_categories = [key for key, _label in Expense.CATEGORY_CHOICES]
    top_customers = list(
        customer_sales.filter(customer__isnull=False)
        .values("customer_id", "customer__name")
        .annotate(
            quantity_sold=Sum("quantity"),
            sales_value=Sum(sales_value_expression),
            amount_received=Sum("amount_paid"),
        )
        .order_by("-sales_value", "customer__name")[:5]
    )

    monthly_rows = year_sales.annotate(month=TruncMonth("date")).values("month").annotate(
        quantity_sold=Sum("quantity"),
        sales_value=Sum(sales_value_expression),
    )
    monthly_data = {row["month"].month: row for row in monthly_rows}
    monthly_expense_rows = year_expenses.annotate(month=TruncMonth("date")).values(
        "month", "category"
    ).annotate(amount_total=Sum("amount"))
    monthly_expense_data = {
        (row["month"].month, row["category"]): row["amount_total"] or Decimal("0.00")
        for row in monthly_expense_rows
    }
    monthly_sales = []
    monthly_costs = []
    for month in range(1, 13):
        row = monthly_data.get(month, {})
        monthly_sales.append({
            "label": date(selected_year, month, 1).strftime("%b"),
            "quantity": row.get("quantity_sold") or 0,
            "sales_value": row.get("sales_value") or Decimal("0.00"),
        })
        monthly_cost = {
            "label": date(selected_year, month, 1).strftime("%b"),
            **{
                category: monthly_expense_data.get((month, category), Decimal("0.00"))
                for category in cost_categories
            },
        }
        monthly_cost["total"] = sum(
            (monthly_cost[category] for category in cost_categories), Decimal("0.00")
        )
        monthly_costs.append(monthly_cost)
    max_monthly_cost = max((item["total"] for item in monthly_costs), default=Decimal("0.00"))
    for item in monthly_costs:
        item["segments"] = {
            category: round(float(item[category] / max_monthly_cost * 100))
            if max_monthly_cost else 0
            for category in cost_categories
        }
    max_monthly_value = max((item["sales_value"] for item in monthly_sales), default=Decimal("0.00"))
    for item in monthly_sales:
        item["bar_width"] = round(float(item["sales_value"] / max_monthly_value * 100)) if max_monthly_value else 0

    max_customer_value = max((item["sales_value"] or Decimal("0.00") for item in top_customers), default=Decimal("0.00"))
    for item in top_customers:
        value = item["sales_value"] or Decimal("0.00")
        item["bar_width"] = round(float(value / max_customer_value * 100)) if max_customer_value else 0

    context = {
        "selected_year": selected_year,
        "years": years,
        "total_quantity": totals["quantity_total"] or 0,
        "total_sales_value": totals["sales_value"] or Decimal("0.00"),
        "total_amount_received": totals["amount_received"] or Decimal("0.00"),
        "sale_count": year_sales.count(),
        "customer_count": customer_sales.filter(customer__isnull=False).values("customer_id").distinct().count(),
        "selected_customer_month": selected_customer_month,
        "customer_month_name": month_name[customer_month_number] if customer_month_number else "",
        "month_choices": [(month, month_name[month]) for month in range(1, 13)],
        "production_total": production_total,
        "top_customers": top_customers,
        "monthly_sales": monthly_sales,
        "cost_categories": Expense.CATEGORY_CHOICES,
        "monthly_costs": monthly_costs,
        "year_expenses": year_expenses,
    }
    return render(request, "core/analytics.html", context)


@login_required
def add_expense(request):
    return expense_form(request)


@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    return expense_form(request, expense)


def expense_form(request, expense=None):
    selected_year = expense.date.year if expense else timezone.localdate().year
    if request.method == "POST":
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            saved_expense = form.save()
            return redirect(f"/analytics/?year={saved_expense.date.year}")
    else:
        initial = {}
        requested_year = request.GET.get("year")
        if requested_year:
            try:
                selected_year = int(requested_year)
                if 1 <= selected_year <= 9999:
                    initial["date"] = date(selected_year, timezone.localdate().month, 1)
            except (TypeError, ValueError):
                selected_year = timezone.localdate().year
        form = ExpenseForm(instance=expense, initial=initial)

    return render(request, "core/add_expense.html", {
        "form": form,
        "expense": expense,
        "selected_year": selected_year,
    })


@require_POST
@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    selected_year = expense.date.year
    expense.delete()
    return redirect(f"/analytics/?year={selected_year}")

@login_required
def add_production(request):
    if request.method == "POST":
        form = ProductionForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("home")

    else:
        form = ProductionForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "core/add_production.html",
        context
    )
