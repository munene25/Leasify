from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from .models import User
from .models import Account
from django import forms
from users.services import user_account_create


class AccountInline(admin.StackedInline):
    model = Account
    can_delete = False  # Since it's a 1:1, you likely don't want to delete just the account
    verbose_name_plural = 'Account Info'
    fk_name = 'user'

# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "is_staff", "is_superuser", "is_active", "phone_number")
    list_select_related = ("account",)
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("is_active", )
    list_select_related = True
    inlines = (AccountInline,)

    def save_model(self, request: HttpRequest, obj: User, form: Any, change: bool) -> None:
        if not change:
            user_account_create(
                email=obj.email,
                password=obj.password,
                first_name=obj.first_name,
                last_name=obj.last_name,
                phone_number=form.cleaned_data.get("phone_number"),
                notify=True
            )
        super().save_model(request, obj, form, change)
    
    def phone_number(self, obj: User) -> str:
        return obj.account.phone_number or "N/A"