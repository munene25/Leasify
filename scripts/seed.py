from users.models import User
from semesters.models import Semester
from payments.models import Payment
from datetime import date
import random
from phonenumber_field.phonenumber import PhoneNumber
from tenancy.services import TenancyCreateService
from semesters.services import SemesterService
from apartments.services import ApartmentCreateService
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
            ("JAN-APR", (1, 1), (4, 30)),
            ("MAY-AUG", (5, 1), (8, 31)),
            ("SEP-DEC", (9, 1), (12, 31)),
        ]
        for year in range(start_year, end_year + 1):
            for name, (sm, sd), (em, ed) in periods:
                sem_name = f"{name}-{year}"
                start = date(year, sm, sd)
                off_season = True if sm == "May" else False
                end = date(year, em, ed)
                semesters.append(
                    {
                        "name": sem_name,
                        "start_date": start,
                        "end_date": end,
                        "off_season": off_season,
                    }
                )
        return semesters

    sems = generate_semesters(2025, 2030)
    semesters = [SemesterService().create(**s) for s in sems]
    sem = Semester.current_semester()
    semester_pk = getattr(sem, "pk")

    no_of_apts = 6
    aps = [{"block": "OLD", "unit_number": i} for i in range(1, no_of_apts + 1)]

    apartments = [ApartmentCreateService(**a).create() for a in aps]

    # Create tenants
    tenancies = [
        TenancyCreateService(
            user_id=i,
            apartment_id=i,
            semester_id=semester_pk,
        ).create()
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
