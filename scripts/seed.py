import random
from decimal import Decimal

from faker import Faker
from django.utils import timezone
from django.conf import settings
from django.core.management import call_command

from leasify.users.models import User
from leasify.apartments.models import Apartment
from leasify.tenancy.services import tenancy_create
from leasify.apartments.services import apartment_create
from leasify.payments.services import payment_alt_create
from leasify.users.services import user_account_create
from leasify.payments.choices import PaymentMode

ITERATIONS = list(range(20))

f = Faker("en_KE")


def dump_data(file_name: str, *app_labels: str):
    """Helper to create fixtures after seeding"""
    with open(settings.APP_DIRS("fixtures/" + file_name), "w") as f:
        call_command("dumpdata", *app_labels, stdout=f, indent=4)

def load_data(file_name: str):
    """Helper for loading fixtures from path"""
    call_command("loaddata",  settings.APP_DIRS(file_name))

def run():
    # ============================================= Roles =============================================
    try:
        load_data("roles.json")
    except Exception:
        call_command("setup_roles")

    # ============================================= Users =============================================
    try:
        load_data("test_users.json")
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
        # create superuser
        User.objects.create_superuser(
            email="edmune25@gmail.com",
            password="Pa55word!",
            first_name="Edwin",
            last_name="Munene",
            phone_number="+254-791-573-104",
            notify=False
        )  # type: ignore
        dump_data("test_users.json", "users")

    # ============================================= Apartments =============================================
    try:
        load_data("test_apartments.json")
        apartments = Apartment.objects.all()
    except Exception:
        NO_OF_APTS = 30
        from leasify.apartments.choices import Wing, Block
        apartments = [
            apartment_create(
                block=random.choice(Block.values),
                unit_number=int(f.building_number()[:4]),
                rent=Decimal(f.numerify("1#000")),
                wing=random.choice(Wing.values),
                floor=random.choice(range(1, 6))
            )
            for _ in range(NO_OF_APTS)
        ]
        dump_data("test_apartments.json", "apartments")

    # ============================================= Tenancies =============================================
    tenancies = [
        tenancy_create(
            user=user,
            apartment=apartments[i],
            start_date=timezone.now().date(),
            duration_months=random.randint(1, 4),
        )
        for i, user in enumerate(users[5:])
    ]

    # ============================================= Payments =============================================
    from leasify.billing.services import billing_period_complete

    for t in tenancies:
        billing = t.billings.latest("pk")
        payment_alt_create(
            billing=billing,
            mode=PaymentMode.MPESA,
            recorded_by=t.user,
        )
        billing_period_complete(billing)