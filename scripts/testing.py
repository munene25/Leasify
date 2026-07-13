from freezegun import freeze_time
from datetime import datetime, timedelta, timezone, date
from pprint import pprint
from django.db import models, connection
from django.utils import timezone as tz
from django.contrib.auth.models import Permission
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from apartments import models as a_models, selectors as a_selectors, services as a_services
from tenancy import models as t_models, selectors as t_selectors, services as t_services
from tenancy.choices import TenancyStatus as TS, TerminationReason as TR
from billing.choices import BillingStatus as BS
from payments import models as p_models, selectors as p_selectors, services as p_services
from users import services as u_services, models as u_models, selectors as u_selectors
from payments.tasks import send_payment_notification
# from tenancy.tasks import notify_reserved_on_expiry

def run():
    # user = u_selectors.user_get(18)
    # apartment = a_selectors.apartment_get_for(user=user, apartment_id=15)
    # tenant = t_services.tenancy_create(user=user, apartment=apartment, start_date=date.today(), duration_months=2)
    # tenant.reservation_expiry = tenant.reservation_expiry - timedelta(1)
    # tenant.save()
    # tenant = t_models.Tenancy.objects.get(pk=17)
    # tenant.reservation_expiry = date.today() + timedelta(1)
    # tenant.save()
    # # send_payment_notification(1)
    # notify_reserved_on_expiry()

    send_payment_notification(payment_id=1, additional_recepients=["edmune25@gmail.com"])