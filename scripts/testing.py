from django.db import models
from users.models import User
from apartments.models import Apartment
from semesters.models import Semester
from semesters.selectors import semester_current
from payments.models import Payment
from tenancy.models import Tenancy
from django.db import connection
from payments.services import PaymentCreateService

def run():
    PaymentCreateService(tenancy_id=1, amount=2000, initiator="tenant", transaction_type="debit").create()