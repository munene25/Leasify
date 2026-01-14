from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from users.models import User

class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = PhoneNumberField(unique=True, blank=False)
    bio = models.TextField(blank=True, max_length=300)
    backup_email = models.EmailField(blank=True, null=True)