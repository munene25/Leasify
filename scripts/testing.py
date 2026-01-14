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
def run():
    user = User.objects.get(pk=2)
    context = {"subject": "Clearance of payment", "user": user, "expiry_hours": timedelta(hours=0.2), "url": "www.bisikaapartments.com", "app_name": "Bisiska apts", "support_email": "support@bisikaapartments.com"}
    email = EmailMultiAlternatives(
        subject="Welcome to Bisika apartments",
        body=render_to_string("emails/verify.txt", context=context),
        from_email="sales@bisikaapartments.com",
        to=[user.email]
        
    )   
    email.attach_alternative(render_to_string("emails/verify.html", context=context), "text/html")
    email.send(fail_silently=False)