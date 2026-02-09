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
from users.services import user_create, user_update
from phonenumber_field.phonenumber import PhoneNumber
from django.contrib.auth.models import Permission

def run():
    all_permissions = Permission.objects.in_bulk(field_name="codename")
    print(f"perms: {all_permissions}")