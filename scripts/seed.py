from decimal import Decimal
from semesters.selectors import semester_current
from semesters.models import Semester
from payments.models import Payment
from users.models import User
from datetime import date
import random
from phonenumber_field.phonenumber import PhoneNumber
from tenancy.services import TenancyService
from semesters.services import SemesterService
from apartments.services import ApartmentService
from payments.services import PaymentCreateService
from users.services import user_account_create
from .permissions import setup_roles_and_permissions
from faker import Faker
from django.core.management import call_command


ITERATIONS = list(range(1, 20))

f = Faker("en_KE")


def run():
    # setup roles and permissions
    try:
        call_command("loaddata", "fixtures/roles.json")
    except Exception:
        setup_roles_and_permissions()

    try:
        call_command("loaddata", "fixtures/test_users.json")
        users = User.objects.all()
    except Exception:
        users = [
            user_account_create(
                password="Pa55word!",
                email=f.email(),
                phone_number=PhoneNumber.from_string(f.numerify("+254-7##-###-###")),
                first_name=f.first_name(),
                last_name=f.last_name(),
                notify = False
            ) for _ in ITERATIONS
        ]
        # create super_user
        user = user_account_create(
            first_name = "Ed",
            last_name = "Mune",
            email = "edmune25@gmail.com",
            phone_number=PhoneNumber.from_string("+254791573104"),
            password = "Pa55word!",
            notify=False
        )
        user.is_superuser = True
        user.is_staff = True
        user.verified = True
        user.save()

    try:
        call_command("loaddata", "fixtures/test_semesters.json")
    except Exception:
        def generate_semesters(start_year=2025, end_year=2029):
            semesters = []
            periods = [
                ((1, 1), (4, 30)),
                ((5, 1), (8, 31)),
                ((9, 1), (12, 31)),
            ]
            for year in range(start_year, end_year + 1):
                for (sm, sd), (em, ed) in periods:
                    start = date(year, sm, sd)
                    off_season = True if sm == 5 else False
                    end = date(year, em, ed)
                    semesters.append(
                        {
                            "start_date": start,
                            "end_date": end,
                            "off_season": off_season,
                        }
                    )
            return semesters

        semesters = [SemesterService().create(**s) for s in generate_semesters(2025, 2030)]

    try:
        call_command("loaddata", "fixtures/test_apartments.json")
    except Exception:

        no_of_apts = len(ITERATIONS) + 5
        aps = [
            {"block": f"{"OLD" if i%2 == 1 else "NEW"}", "unit_number": i, "rent": Decimal(20000)}
            for i in range(1, no_of_apts + 1)
        ]

        apartments = [ApartmentService().create(**a) for a in aps]

    curr_sem = semester_current().pk
    tenancies = [
        TenancyService().create(
            user_id=i,
            apartment_id=i,
            semester_id=curr_sem,
        )
        for i in ITERATIONS
    ]

    # Create payments
    for num in ITERATIONS:
        for _ in range(1, 4):
            try:
                PaymentCreateService(
                    amount=random.randint(2, 7) * 1000,
                    transaction_type="debit",
                    tenancy_id=num,
                    initiator="tenant",
                    phone_number=users[num].account.phone_number #type: ignore
                ).create()
            except:
                pass

    