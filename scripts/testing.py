from django.db import models
from users.models import User
from apartments.models import Apartment
from semesters.models import Semester
from semesters.selectors import semester_current
from payments.models import Payment
from tenancy.models import Tenancy
from django.db import connection
from payments.services import PaymentCreateService
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from datetime import timedelta
from users.services import user_create
from phonenumber_field.phonenumber import PhoneNumber


def run():
    phone_number = PhoneNumber.from_string("0721 321 231")
    user_create(
        email="wallace@gmail.com",
        password="alsdk33-9u-v09uda",
        phone_number=phone_number,
        notify=True,
        first_name="Wallace",
        last_name="Pimbo",
    )
