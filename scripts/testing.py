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
from payments.choices import PaymentInitiator

def run():
    
    tenant = t_selectors.tenancy_in([TS.RESERVED]).latest("created_at")
    # t_services.tenancy_renew_lease(tenant, 2)
    billing = tenant.billings.latest("start_date")
    if billing:
        p_services.payment_initiate(
            billing, 
            "254791573104", 
            initiator=PaymentInitiator.ADMIN, 
            stk_push=True
        ) 