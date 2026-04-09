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
from users.services import user_account_create, user_authenticate
from django.contrib.auth.models import Permission

def run():
    pass