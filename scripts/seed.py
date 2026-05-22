from decimal import Decimal
from users.models import User
from apartments.models import Apartment
import random
from tenancy.services import tenancy_create
from apartments.services import apartment_create
from payments.services import payment_initiate, payment_confirm
from payments.mpesa import CallbackResponse
from users.services import user_account_create
from scripts.permissions import setup_roles_and_permissions
from faker import Faker
from django.core.management import call_command
from payments.choices import PaymentInitiator
from django.utils import timezone

ITERATIONS = list(range(20))

f = Faker("en_KE")


def dump_data(file_name: str, *app_labels: str):
    with open(file_name, "w") as f:
        call_command("dumpdata", *app_labels, stdout=f, indent=4)


def run():
    # ============================================= Roles =============================================
    try:
        call_command("loaddata", "fixtures/roles.json")
    except Exception:
        setup_roles_and_permissions()
        dump_data("fixtures/roles.json", "auth.Permission", "auth.Group")

    # ============================================= Users =============================================
    try:
        call_command("loaddata", "fixtures/test_users.json")
        users = User.objects.all()
    except Exception:
        users = [
            user_account_create(
                password="Pa55word!",
                email=f.email(),
                phone_number=f.numerify("+2547########"),
                first_name=f.first_name(),
                last_name=f.last_name(),
                notify=False,
            )
            for _ in ITERATIONS
        ]
        # create super_user
        User.objects.create_superuser(
            email="edmune25@gmail.com",
            password="Pa55word!",
            first_name="Edwin",
            last_name="Munene",
            phone_number="+254-791-573-104",
        )  # type: ignore
        dump_data("fixtures/test_users.json", "users")

    # ============================================= Apartments =============================================
    try:
        call_command("loaddata", "fixtures/test_apartments.json")
        apartments = Apartment.objects.all()
    except Exception:

        NO_OF_APTS = 30
        apartments = [
            apartment_create(
                block=random.choice(Apartment.Block.values),
                unit_number=int(f.building_number()),
                rent=Decimal(f.numerify("1#000")),
            )
            for _ in range(NO_OF_APTS)
        ]
        dump_data("fixtures/test_apartments.json", "apartments")

    # ============================================= Tenancies =============================================
    tenancies = [
        tenancy_create(
            user=users[i],
            apartment=apartments[i],
            start_date=timezone.now().date(),
            duration_months=random.randint(1, 4),
        )
        for i in ITERATIONS
    ]

    # ============================================= Payments =============================================
    from billing.services import billing_period_confirm_payment

    for t in tenancies:
        billing = t.last_billing
        if not billing:
            raise ValueError("billing not created")
        p = payment_initiate(
            billing=billing,
            initiator=PaymentInitiator.TENANT,
            phone_number=f.numerify("+2547########"),
            stk_push=False,
        )
        confirmed = payment_confirm(
            CallbackResponse(
                checkout_id=p.checkout_id,
                success=True,
                result_desc="Payment completed successfuly",
                receipt_no=f.bothify("????#???#??").upper(),
            )
        )
        billing_period_confirm_payment(billing, confirmed)
