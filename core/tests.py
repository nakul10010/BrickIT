from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import BrickType, Expense, Inventory, Production
from Sales.models import Customer, Sales


class AuthenticatedTestMixin:
    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(username="test-user", password="test-password")
        self.client.force_login(user)


class AuthenticationAccessTest(TestCase):
    def test_login_page_is_public(self):
        response = self.client.get("/accounts/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to manage Gomti Bricks")

    def test_business_pages_require_login(self):
        protected_paths = (
            "/",
            "/analytics/",
            "/sales/",
            "/customers/",
            "/deliveries/",
            "/employees/",
            "/employees/attendance/",
            "/production/add/",
            "/expenses/add/",
        )
        for path in protected_paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith("/accounts/login/?next="))

    def test_login_and_post_logout(self):
        get_user_model().objects.create_user(
            username="owner",
            password="safe-test-password",
        )
        response = self.client.post("/accounts/login/", {
            "username": "owner",
            "password": "safe-test-password",
        })

        self.assertRedirects(response, "/")
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        response = self.client.post("/accounts/logout/")
        self.assertRedirects(response, "/accounts/login/")

class ProductionInventoryTest(TestCase):

    def test_new_production_increases_inventory(self):
        brick_type = BrickType.objects.create(name="4-inch")

        inventory = Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        Production.objects.create(
            brick_type=brick_type,
            quantity=500
        )

        inventory.refresh_from_db()

        self.assertEqual(inventory.quantity, 1500)

    def test_editing_production_uses_only_the_difference(self):
        brick_type = BrickType.objects.create(name="4-inch")

        inventory = Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        production = Production.objects.create(
            brick_type=brick_type,
            quantity=500
        )

        production.quantity = 700
        production.save()

        inventory.refresh_from_db()

        self.assertEqual(inventory.quantity, 1700)

    def test_changing_brick_type_moves_inventory(self):
        four_inch = BrickType.objects.create(name="4-inch")
        six_inch = BrickType.objects.create(name="6-inch")

        four_inch_inventory = Inventory.objects.create(
            brick_type=four_inch,
            quantity=1000
        )

        six_inch_inventory = Inventory.objects.create(
            brick_type=six_inch,
            quantity=2000
        )

        production = Production.objects.create(
            brick_type=four_inch,
            quantity=500
        )

        production.brick_type = six_inch
        production.save()

        four_inch_inventory.refresh_from_db()
        six_inch_inventory.refresh_from_db()

        self.assertEqual(four_inch_inventory.quantity, 1000)
        self.assertEqual(six_inch_inventory.quantity, 2500)

    def test_deleting_production_reduces_inventory(self):
        brick_type = BrickType.objects.create(name="4-inch")

        inventory = Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        production = Production.objects.create(
            brick_type=brick_type,
            quantity=500
        )

        production.delete()

        inventory.refresh_from_db()

        self.assertEqual(inventory.quantity, 1000)

class ProductionPageTest(AuthenticatedTestMixin, TestCase):

    def test_add_production_page(self):
        response = self.client.get(
            "/production/add/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Production")
        self.assertContains(response, "Save Production")

    def test_add_production_form(self):
        brick_type = BrickType.objects.create(
            name="4-inch"
        )

        inventory = Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        response = self.client.post(
            "/production/add/",
            {
                "brick_type": brick_type.id,
                "quantity": 100,
                "date": "2026-09-13",
            }
        )

        inventory.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Production.objects.count(), 1)
        self.assertEqual(inventory.quantity, 1100)


class AnalyticsPageTest(AuthenticatedTestMixin, TestCase):
    def test_analytics_summarizes_selected_year(self):
        brick_type = BrickType.objects.create(name="4-inch")
        Inventory.objects.create(brick_type=brick_type, quantity=100)
        customer = Customer.objects.create(name="Top Customer")
        Sales.objects.create(
            customer=customer,
            brick_type=brick_type,
            quantity=20,
            price_per_brick=Decimal("12.50"),
            amount_paid=Decimal("100.00"),
            date="2026-03-10",
        )
        Production.objects.create(
            brick_type=brick_type,
            quantity=30,
            date="2026-04-10",
        )

        response = self.client.get("/analytics/?year=2026")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_quantity"], 20)
        self.assertEqual(response.context["total_sales_value"], Decimal("250.00"))
        self.assertEqual(response.context["total_amount_received"], Decimal("100.00"))
        self.assertEqual(response.context["production_total"], 30)
        self.assertEqual(response.context["top_customers"][0]["customer__name"], "Top Customer")
        self.assertEqual(len(response.context["monthly_sales"]), 12)

    def test_analytics_handles_year_without_sales(self):
        response = self.client.get("/analytics/?year=2025")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_quantity"], 0)
        self.assertEqual(response.context["total_sales_value"], Decimal("0.00"))
        self.assertEqual(response.context["top_customers"], [])

    def test_analytics_compares_expenses_by_category_and_month(self):
        Expense.objects.create(
            category=Expense.ELECTRICITY,
            amount=Decimal("1250.00"),
            date="2026-02-10",
        )
        Expense.objects.create(
            category=Expense.FUEL,
            amount=Decimal("800.00"),
            date="2026-02-15",
        )
        Expense.objects.create(
            category=Expense.MISCELLANEOUS,
            amount=Decimal("400.00"),
            date="2026-03-02",
        )

        response = self.client.get("/analytics/?year=2026")

        self.assertEqual(response.context["monthly_costs"][1]["total"], Decimal("2050.00"))
        self.assertEqual(response.context["monthly_costs"][2][Expense.MISCELLANEOUS], Decimal("400.00"))
        self.assertEqual(
            sum((month["total"] for month in response.context["monthly_costs"]), Decimal("0.00")),
            Decimal("2450.00"),
        )
        self.assertEqual(sum(response.context["monthly_costs"][1]["segments"].values()), 100)
        self.assertContains(response, "cost-chart-details")
        self.assertContains(response, 'data-month="Feb 2026"')
        self.assertNotContains(response, "cost-comparison-table")

    def test_expense_can_be_recorded_from_form(self):
        response = self.client.post("/expenses/add/", {
            "category": Expense.FUEL,
            "amount": "950.50",
            "date": "2026-05-12",
            "note": "Diesel",
        })

        self.assertRedirects(response, "/analytics/?year=2026")
        expense = Expense.objects.get()
        self.assertEqual(expense.category, Expense.FUEL)
        self.assertEqual(expense.amount, Decimal("950.50"))

    def test_top_customers_can_be_filtered_to_one_month(self):
        brick_type = BrickType.objects.create(name="4-inch")
        Inventory.objects.create(brick_type=brick_type, quantity=1000)
        february_customer = Customer.objects.create(name="February Customer")
        march_customer = Customer.objects.create(name="March Customer")
        Sales.objects.create(
            customer=february_customer,
            brick_type=brick_type,
            quantity=10,
            price_per_brick=Decimal("10.00"),
            date="2026-02-10",
        )
        Sales.objects.create(
            customer=march_customer,
            brick_type=brick_type,
            quantity=20,
            price_per_brick=Decimal("10.00"),
            date="2026-03-10",
        )

        response = self.client.get("/analytics/?year=2026&customer_month=2")

        self.assertEqual(response.context["customer_month_name"], "February")
        self.assertEqual(response.context["customer_count"], 1)
        self.assertEqual(
            response.context["top_customers"][0]["customer__name"],
            "February Customer",
        )
        self.assertEqual(response.context["total_quantity"], 30)
