from users.models import User
from apartments.models import Apartment
from semesters.models import Semester
from semesters.selectors import semester_current
from payments.models import Payment
from tenancy.models import Tenancy
from django.utils import timezone
from django.db import connection, transaction, models
import random
from phonenumber_field.phonenumber import PhoneNumber
from phonenumber_field.serializerfields import PhoneNumberField
from pprint import pprint
from decimal import Decimal


def run():
    @transaction.atomic
    def create_user():
        last_user = User.objects.select_for_update().order_by("-id").first()
        i = (last_user.pk if last_user else 0) + 1
        phone_number = f"0700 000 00{i}" if i < 10 else f"0700 000 0{i}"
        user = User(
            email=f"edmune25+{i}@gmail.com",
            username=f"munene{i}",
            phone_number=phone_number,
            first_name=f"ed{i}",
            last_name=f"mune{i}",
        )
        user.set_password("password")
        user.save()
        return user

    @transaction.atomic
    def create_payment(
        amount: int,
        tenancy_pk: int,
        transaction_type: str = "debit",
        name: str = "admin user",
    ):
        last_payment = (
            Payment.objects.filter(ref_no__startswith="A").select_for_update().count()
        )
        next_number = last_payment + 1
        ref_no = f"AIT-{next_number:06d}"  # eg AIT-000123 - Admin Initiated Paymets
        payment = Payment.objects.create(
            ref_no=ref_no,
            amount=amount,
            transaction_type=transaction_type,
            phone_number="0722 222 222",
            full_name=name,
            tenancy=Tenancy.objects.get(pk=tenancy_pk),
            created_at=timezone.now(),
        )
        return payment

    @transaction.atomic
    def create_apartment(block=None, unit_number=None):
        if not block:
            block = random.choice(Apartment.ApartmentChoices.values)
        last_apt = (
            unit_number
            if unit_number
            else Apartment.objects.filter(block=block).order_by("unit_number").last()
        )
        i = (last_apt.unit_number if last_apt else 0) + 1

        apartment = Apartment.objects.create(
            block=block,
            unit_number=i,
        )
        return apartment

    def delete_payment(ref_no):
        Payment.objects.get(ref_no=ref_no).delete()

    @transaction.atomic
    def create_tenancy():
        homeless_user = User.objects.filter(
            models.Q(tenancy__isnull=True) | models.Q(tenancy__is_active=False)
        ).first()
        empty_home = Apartment.objects.filter(tenancy__isnull=True).first()
        if not empty_home:
            empty_home = create_apartment()
        if not homeless_user:
            homeless_user = create_user()
        tenancy = Tenancy.objects.create(
            user=homeless_user,
            apartment=empty_home,
            semester=semester_current(),
        )
        return tenancy

    def create_tenancy_for_a_semester(tenancy=None, semester=None):
        if not tenancy:
            count = Tenancy.objects.count()
            rand_int = random.randint(1, count)
            tenancy = Tenancy.objects.filter(pk=rand_int).first()

        next_semester = (
            Semester.objects.get(pk=semester.pk)
            if semester
            else Semester.objects.get(pk=tenancy.semester.pk + 1)
        )

        with transaction.atomic():
            instance, created = Tenancy.objects.get_or_create(
                user=tenancy.user,
                semester=next_semester,
                apartment=tenancy.apartment,
            )
        return instance, created
