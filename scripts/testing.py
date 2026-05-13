from freezegun import freeze_time
from datetime import datetime, timedelta, timezone
from pprint import pprint
from django.db import models, connection
from django.utils import timezone as tz
from django.contrib.auth.models import Permission
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from apartments import models as a_models, selectors as a_selectors, services as a_services
from semesters import models as s_models, selectors as s_selectors
from tenancy import models as t_models, selectors as t_selectors, services as t_services
from payments import models as p_models, selectors as p_selectors, services as p_services
from users import services as u_services, models as u_models, selectors as u_selectors

def run():
    user = u_models.User.objects.get(pk=5)
    semester = s_selectors.semester_current()
    tenant = t_selectors.tenancy_recent(user)
    print("Recent apartment for user", tenant.apartment_id)
    
    apt_list = a_selectors.apartment_list_for(user=user)
    rentable = a_models.Apartment.objects.filter(rentable=True)
    pprint([{"apartment_id": apt.pk, "rentable": apt.rentable} for apt in apt_list])
    pprint([{"apartment_id": apt.pk, "rentable": apt.rentable} for apt in rentable])
    