from django.db import models
from users.models import User
from apartments.models import Apartment
from semesters.models import Semester
from payments.models import Payment
from tenancy.models import Tenancy


def run():
    current_tenant = Tenancy.objects.filter(
        apartment=models.OuterRef("pk"), semester_id=3
    )
   
    occupied_apts = Apartment.objects.annotate(
        tenant=models.Subquery(current_tenant.values("total_paid"))
    ).all()

    for apt in occupied_apts:
        print(apt, getattr(apt, "tenant"))
