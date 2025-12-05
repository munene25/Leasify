from decimal import Decimal
from users.models import User
from semesters.selectors import semester_current
from payments.models import Payment
from datetime import date
import random
from phonenumber_field.phonenumber import PhoneNumber
from tenancy.services import TenancyService
from semesters.services import SemesterService
from apartments.services import ApartmentService
from payments.services import PaymentCreateService


def run():
    # Create users (use bulk_create for performance)
    given_range = list(range(1, 10))
    users_data = [
        User(
            email=f"edmune25+{i}@gmail.com",
            username=f"munene{i}",
            phone_number=PhoneNumber.from_string(f"0700 000 00{i}", region="KE"),
            first_name=f"ed{i}",
            last_name=f"mune{i}",
        )
        for i in given_range
    ]
    users = User.objects.bulk_create(users_data)

    # Set passwords (must call set_password + save individually)
    for u in users:
        u.set_password("password")
        u.save(update_fields=["password"])

    # Create semesters

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
    no_of_apts = 12
    aps = [
        {"block": f"{"OLD" if i%2 == 1 else "NEW"}", "unit_number": i, "rent": Decimal(20000)}
        for i in range(1, no_of_apts + 1)
    ]

    apartments = [ApartmentService().create(**a) for a in aps]

    # Create tenants
    tenancies = [
        TenancyService().create(
            user_id=i,
            apartment_id=i,
            semester_id=semester_current().pk,
        )
        for i in given_range
    ]

    # Create payments
    for num in given_range:
        for _ in range(1, 4):
            try:
                PaymentCreateService(
                    amount=random.randint(2, 7) * 1000,
                    transaction_type="debit",
                    tenancy_id=num,
                    initiator="tenant",
                ).create()
            except:
                pass

    User.objects.create_superuser(
        email="edmune25@gmail.com",
        password="password",
        phone_number="0700000000",
        username="edmune",
    )
