from django.db import models

class AccountType(models.TextChoices):
    """Mode of registration"""
    
    EMAIL = "email", "Email"
    GOOGLE = "google", "Google"
