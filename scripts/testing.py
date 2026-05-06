from freezegun import freeze_time
from datetime import datetime, timedelta, timezone
from django.db import models, connection
from django.utils import timezone as tz
from django.contrib.auth.models import Permission
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from users.models import User
from apartments.models import Apartment
from semesters import models, selectors as sem_selectors
from semesters.selectors import semester_current
from payments.models import Payment
from tenancy.models import Tenancy
from payments.services import PaymentCreateService
from users.services import user_account_create, user_authenticate

def run():
    s = semester_current().start_date
    before = datetime(s.year, s.month, s.day, tzinfo=timezone.utc)
    print("Starting at: " ,before.date(), before.time())
    with freeze_time(before, tz_offset=0) as frozen_time:
        prev_sem = sem_selectors.semester_within_grace_period()
        print("Current grace period semester:\t", prev_sem, "\n")
        
        one_week_later = before + timedelta(weeks=1)
        frozen_time.move_to(one_week_later)
        print("Frozen date one week later:", tz.now().date())
        prev_sem = sem_selectors.semester_within_grace_period()
        print("Semester:\t" ,prev_sem, "\n")
        
        two_weeks_later = before + timedelta(weeks=2)
        frozen_time.move_to(two_weeks_later)
        print("Frozen date two weeks later:", tz.now().date())
        prev_sem = sem_selectors.semester_within_grace_period()
        print("Semester:\t" ,prev_sem, "\n")
        
        two_weeks_one_hour_later = before + timedelta(weeks=2, hours=1)
        frozen_time.move_to(two_weeks_one_hour_later)
        print("Frozen date two weeks later:", tz.now().date())
        prev_sem = sem_selectors.semester_within_grace_period()
        print("Semester:\t", prev_sem, "\n")
        
