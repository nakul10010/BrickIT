from django.test import TestCase
from django.contrib.auth import get_user_model

# Create your tests here.
from django.test import TestCase

from core.models import BrickType, Inventory
from .models import Sales, Customer
from django.core.exceptions import ValidationError
from decimal import Decimal


class AuthenticatedTestMixin:
    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(username="test-user", password="test-password")
        self.client.force_login(user)

class SalesInventoryTest(TestCase):

    def test_new_sale_reduces_inventory(self):
        brick_type = BrickType.objects.create(name="4-inch")

        inventory = Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        Sales.objects.create(
            brick_type=brick_type,
            quantity=200
        )

        inventory.refresh_from_db()

        self.assertEqual(inventory.quantity, 800)
    def test_editing_sale_uses_only_the_difference(self):
        brick_type = BrickType.objects.create(name="4-inch")

        inventory = Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        sale = Sales.objects.create(
            brick_type=brick_type,
            quantity=200
        )

        sale.quantity = 300
        sale.save()

        inventory.refresh_from_db()

        self.assertEqual(inventory.quantity, 700)

    def test_changing_brick_type_moves_sale(self):
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

        sale = Sales.objects.create(
            brick_type=four_inch,
            quantity=200
        )

        sale.brick_type = six_inch
        sale.save()

        four_inch_inventory.refresh_from_db()
        six_inch_inventory.refresh_from_db()

        self.assertEqual(four_inch_inventory.quantity, 1000)
        self.assertEqual(six_inch_inventory.quantity, 1800)

    def test_deleting_sale_returns_inventory(self):
        brick_type = BrickType.objects.create(name="4-inch")

        inventory = Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        sale = Sales.objects.create(
            brick_type=brick_type,
            quantity=200
        )

        sale.delete()

        inventory.refresh_from_db()

        self.assertEqual(inventory.quantity, 1000)

    def test_sale_cannot_exceed_inventory(self):
        brick_type = BrickType.objects.create(name="4-inch")

        inventory = Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        with self.assertRaises(ValidationError):
            Sales.objects.create(
                brick_type=brick_type,
                quantity=1200
            )

        inventory.refresh_from_db()

        self.assertEqual(inventory.quantity, 1000)

    def test_sale_total_amount(self):
        brick_type = BrickType.objects.create(name="4-inch")

        Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        sale = Sales.objects.create(
            brick_type=brick_type,
            quantity=200,
            price_per_brick=Decimal("7.50")
        )

        self.assertEqual(
            sale.total_amount(),
            Decimal("1500.00")
        )

    def test_pending_deliveries_count(self):
        brick_type = BrickType.objects.create(name="4-inch")

        Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        Sales.objects.create(
            brick_type=brick_type,
            quantity=100,
            is_delivered=False
        )

        Sales.objects.create(
            brick_type=brick_type,
            quantity=100,
            is_delivered=True
        )

        pending_count = Sales.objects.filter(
            is_delivered=False
        ).count()

        self.assertEqual(pending_count, 1)

    def test_sale_amount_due(self):
        brick_type = BrickType.objects.create(name="4-inch")

        Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        sale = Sales.objects.create(
            brick_type=brick_type,
            quantity=100,
            price_per_brick=Decimal("7.50"),
            amount_paid=Decimal("500.00")
        )

        self.assertEqual(
            sale.amount_due(),
            Decimal("250.00")
        )
    def test_customer_total_due(self):
        customer = Customer.objects.create(
            name="ABC Builders"
        )

        brick_type = BrickType.objects.create(name="4-inch")

        Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        Sales.objects.create(
            customer=customer,
            brick_type=brick_type,
            quantity=100,
            price_per_brick=Decimal("7.50"),
            amount_paid=Decimal("500.00")
        )

        self.assertEqual(
            customer.total_due(),
            Decimal("250.00")
        )
class CustomerPageTest(AuthenticatedTestMixin, TestCase):

    def test_customer_list_page(self):
        Customer.objects.create(
            name="ABC Builders",
            phone_number="9876543210"
        )

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ABC Builders")
        self.assertContains(response, f'aria-label="View all sales for ABC Builders"')

    def test_customer_detail_page(self):
        customer = Customer.objects.create(
            name="ABC Builders",
            phone_number="9876543210"
        )
        brick_type = BrickType.objects.create(name="4-inch")
        Inventory.objects.create(brick_type=brick_type, quantity=100)
        Sales.objects.create(
            customer=customer,
            brick_type=brick_type,
            quantity=12,
            price_per_brick=Decimal("5.00"),
        )

        response = self.client.get(
            f"/customers/{customer.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ABC Builders")
        self.assertContains(response, "9876543210")
        self.assertContains(response, "Sales history")
        self.assertContains(response, "12")

    def test_add_sale_page(self):
        response = self.client.get("/sales/add/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Sale")
        self.assertContains(response, "Save Sale")
        for method in ("Cash", "Card", "Cheque", "UPI"):
            self.assertContains(response, method)

    def test_add_sale_form(self):
        customer = Customer.objects.create(
            name="ABC Builders"
        )

        brick_type = BrickType.objects.create(
            name="4-inch"
        )

        inventory = Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        response = self.client.post(
            "/sales/add/",
            {
                "customer": customer.id,
                "brick_type": brick_type.id,
                "quantity": 100,
                "price_per_brick": "7.50",
                "amount_paid": "0",
                "payment_method": "cash",
                "date": "2026-09-13",
            }
        )

        inventory.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Sales.objects.count(), 1)
        self.assertEqual(inventory.quantity, 900)
        self.assertEqual(Sales.objects.get().payment_method, "cash")

    def test_add_sale_can_create_new_customer_inline(self):
        brick_type = BrickType.objects.create(name="4-inch")
        Inventory.objects.create(brick_type=brick_type, quantity=1000)

        response = self.client.post(
            "/sales/add/",
            {
                "customer": "",
                "new_customer_name": "Fresh Customer",
                "new_customer_phone": "9876543210",
                "new_customer_address": "22 Lake Road",
                "brick_type": brick_type.id,
                "quantity": 10,
                "price_per_brick": "7.50",
                "amount_paid": "0",
                "payment_method": "upi",
                "date": "2026-10-22",
                "delivery_date": "2026-10-25",
                "delivery_time": "11:00",
                "delivery_address": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        customer = Customer.objects.get(name="Fresh Customer")
        self.assertEqual(customer.phone_number, "9876543210")
        self.assertEqual(customer.address, "22 Lake Road")
        sale = Sales.objects.get(customer=customer)
        self.assertEqual(sale.delivery_address, "22 Lake Road")
        self.assertEqual(sale.payment_method, "upi")
class SalesListPageTest(AuthenticatedTestMixin, TestCase):

    def test_sales_summary(self):
        customer = Customer.objects.create(
            name="ABC Builders"
        )

        brick_type = BrickType.objects.create(
            name="4-inch"
        )

        Inventory.objects.create(
            brick_type=brick_type,
            quantity=1000
        )

        Sales.objects.create(
            customer=customer,
            brick_type=brick_type,
            quantity=100,
            price_per_brick=Decimal("7.50"),
            amount_paid=Decimal("500.00")
        )

        response = self.client.get("/sales/")

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context["total_quantity"],
            100
        )

        self.assertEqual(
            response.context["total_amount"],
            Decimal("750.00")
        )

        self.assertEqual(
            response.context["total_due"],
            Decimal("250.00")
        )


class DeliveryPageTest(AuthenticatedTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(
            name="ABC Builders",
            address="12 Main Road, Kalmeshwar",
        )
        self.brick_type = BrickType.objects.create(name="4-inch")
        Inventory.objects.create(brick_type=self.brick_type, quantity=1000)
        self.sale = Sales.objects.create(
            customer=self.customer,
            brick_type=self.brick_type,
            quantity=100,
            delivery_date="2026-10-28",
            delivery_time="10:30",
            delivery_address=self.customer.address,
        )

    def test_delivery_page_shows_pending_schedule_and_address(self):
        response = self.client.get("/deliveries/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pending deliveries")
        self.assertContains(response, "Delivered")
        self.assertContains(response, "28/10/2026")
        self.assertContains(response, "10:30 AM")
        self.assertContains(response, "12 Main Road, Kalmeshwar")

    def test_mark_delivered_updates_sale_status(self):
        response = self.client.post(f"/deliveries/{self.sale.id}/delivered/")

        self.assertRedirects(response, "/deliveries/")
        self.sale.refresh_from_db()
        self.assertTrue(self.sale.is_delivered)

    def test_mark_not_delivered_returns_sale_to_pending(self):
        self.sale.is_delivered = True
        self.sale.save(update_fields=["is_delivered"])

        response = self.client.post(f"/deliveries/{self.sale.id}/not-delivered/")

        self.assertRedirects(response, "/deliveries/")
        self.sale.refresh_from_db()
        self.assertFalse(self.sale.is_delivered)

    def test_delivery_page_handles_walk_in_sale_without_address(self):
        Sales.objects.create(
            brick_type=self.brick_type,
            quantity=5,
        )

        response = self.client.get("/deliveries/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Walk-in customer")
        self.assertContains(response, "Address not provided")


class SalesFiltersTest(AuthenticatedTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.four_inch = BrickType.objects.create(name="4-inch")
        self.six_inch = BrickType.objects.create(name="6-inch")
        Inventory.objects.create(brick_type=self.four_inch, quantity=1000)
        Inventory.objects.create(brick_type=self.six_inch, quantity=1000)
        self.low_sale = Sales.objects.create(
            brick_type=self.four_inch,
            quantity=10,
            price_per_brick=Decimal("5.00"),
            date="2026-09-03",
        )
        self.high_sale = Sales.objects.create(
            brick_type=self.four_inch,
            quantity=2,
            price_per_brick=Decimal("100.00"),
            date="2026-09-13",
        )
        self.other_month_sale = Sales.objects.create(
            brick_type=self.six_inch,
            quantity=1,
            price_per_brick=Decimal("100.00"),
            date="2026-10-01",
        )

    def test_sort_by_amount_low_to_high(self):
        response = self.client.get("/sales/?sort=amount_asc")
        sales = list(response.context["all_sales"])
        self.assertEqual(
            [sale.id for sale in sales],
            [self.low_sale.id, self.other_month_sale.id, self.high_sale.id],
        )

    def test_filter_by_month_and_brick_type(self):
        response = self.client.get(
            f"/sales/?month=2026-09&brick_type={self.four_inch.id}"
        )
        sales = list(response.context["all_sales"])
        self.assertEqual(
            {sale.id for sale in sales},
            {self.low_sale.id, self.high_sale.id},
        )
        self.assertEqual(response.context["total_quantity"], 12)

    def test_filter_by_year_includes_every_month_of_that_year(self):
        response = self.client.get("/sales/?year=2026")
        sales = list(response.context["all_sales"])

        self.assertEqual(
            {sale.id for sale in sales},
            {self.low_sale.id, self.high_sale.id, self.other_month_sale.id},
        )
        self.assertEqual(response.context["total_quantity"], 13)
        self.assertEqual(response.context["selected_year"], 2026)
