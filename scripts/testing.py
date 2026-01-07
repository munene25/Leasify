from django.db import models
from users.models import User
from apartments.models import Apartment
from semesters.models import Semester
from semesters.selectors import semester_current
from payments.models import Payment
from tenancy.models import Tenancy
from django.db import connection
import time

def run():
    print(semester_current())
    time.sleep(5)
    print(semester_current())
    time.sleep(6)
    print(semester_current())

    print(connection.queries)
