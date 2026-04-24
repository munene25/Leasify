from decimal import Decimal
from semesters.selectors import semester_current
from semesters.models import Semester
from payments.models import Payment
from users.models import User
from datetime import date
import random
from tenancy.services import TenancyService
from semesters.services import semester_create
from apartments.services import apartment_create
from payments.services import PaymentCreateService
from users.services import user_account_create
from .permissions import setup_roles_and_permissions
from faker import Faker
from django.core.management import call_command


ITERATIONS = list(range(1, 20))

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
                phone_number=f.numerify("+254-7##-###-###"),
                first_name=f.first_name(),
                last_name=f.last_name(),
                notify = False
            ) for _ in ITERATIONS
        ]
        # create super_user
        User.objects.create_superuser(
            email="edmune25@gmail.com",
            password="Pa55word!",
            first_name="Edwin",
            last_name="Munene",
            phone_number="+254-791-573-104",
        ) # type: ignore
        dump_data("fixtures/test_users.json", "users")



    # ============================================= Semesters =============================================
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

        [semester_create(**s) for s in generate_semesters(2025, 2030)]
        dump_data("fixtures/test_semesters.json", "semesters")


    # ============================================= Apartments =============================================
    try:
        call_command("loaddata", "fixtures/test_apartments.json")
    except Exception:

        no_of_apts = len(ITERATIONS) + 5
        aps = [
            {"block": f"{"OLD" if i%2 == 1 else "NEW"}", "unit_number": i, "rent": Decimal(20000)}
            for i in range(1, no_of_apts + 1)
        ]

        apartments = [apartment_create(**a) for a in aps]
        dump_data("fixtures/test_apartments.json", "apartments")



    # ============================================= Tenancies =============================================
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

    