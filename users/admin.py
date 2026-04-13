from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from .models import User
from .models import Account
from django import forms
from structlog import get_logger

logger = get_logger("users.admin")


# Account inline model
class AccountInline(admin.StackedInline):
    model = Account
    can_delete = False
    max_num = 1
    extra = 1
    verbose_name_plural = "Account Info"
    exclude = (
        "user",
        "created_at",
    )
    fk_name = "user"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "is_staff", "is_superuser", "is_active", "phone_number")
    list_select_related = ("account",)
    exclude = ("last_login", "created_at", "last_email_change")
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("is_active",)
    list_select_related = True
    inlines = (AccountInline,)

    def phone_number(self, obj: User) -> str:
        """This is the derived field for the list_display"""
        return obj.account.phone_number or "N/A"

    def save_model(self, request: HttpRequest, obj: User, form: Any, change: bool) -> None:
        if change:
            from django.contrib.auth.models import BaseUserManager

            if "email" in form.cleaned_data:
                form.cleaned_data["email"] = BaseUserManager.normalize_email(form.cleaned_data["email"])

            if "password" in form.cleaned_data:
                password = form.cleaned_data.pop("password")
                obj.set_password(password)
                obj.save(update_fields="password")
                logger.info(f"admin changed [user_id: {obj.pk}] password")

            super().save_model(request, obj, form, change)
            logger.info(f"admin updated [user_id: {obj.pk}] data. changes[{list(form.cleaned_data.keys())}]")

        else:
            from users.services import user_account_create

            user_account_create(
                email=obj.email, password=obj.password, first_name=obj.first_name, last_name=obj.last_name, notify=True
            )

    def save_related(self, request, form, formsets, change):
        # Since you have exactly one inline
        account_formset = formsets[0]
        
        # Check if the formset has valid data and is not marked for deletion
        if account_formset.has_changed() and account_formset.is_valid():
            # Get the cleaned data from the first form in the set
            # (Using .get(0) style or index 0 for 1:1)
            form_data = account_formset.forms[0].cleaned_data
            
            # Remove the internal 'id' or 'user' key if it exists to avoid 
            # passing redundant objects to your service
            form_data.pop('id', None)
            form_data.pop('user', None)

            from users.services import account_create, user_update
            
            if not change:
                # CREATE flow
                account_create(user=form.instance, **form_data)
            else:
                # UPDATE flow
                user_update(user=form.instance, **form_data)