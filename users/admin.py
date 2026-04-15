from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from .models import User
from .models import Account
from django import forms
from structlog import get_logger
from django.contrib.auth.models import BaseUserManager


logger = get_logger("users.admin")

class AccountAdminForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = "__all__"

    def clean_backup_email(self):
        value = self.cleaned_data.get("backup_email")
        if value:
            return BaseUserManager.normalize_email(value)
        return value

class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"

    def clean_email(self):
        value = self.cleaned_data.get("email")
        if value:
            return BaseUserManager.normalize_email(value)
        return value
    
# Account inline model
class AccountInline(admin.StackedInline):
    model = Account
    form = AccountAdminForm
    can_delete = False
    max_num = 1
    extra = 1
    verbose_name_plural = "Account Info"
    exclude = (
        "created_at",
    )
    fk_name = "user"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "is_staff", "is_superuser", "is_active", "phone_number")
    list_select_related = ("account",)
    form = UserAdminForm
    exclude = ("last_login", "created_at", "last_email_change")
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("is_active",)
    can_delete = False
    list_select_related = True
    inlines = (AccountInline,)

    def phone_number(self, obj: User) -> str:
        """This is the derived field for the list_display"""
        return obj.account.phone_number or "N/A"

    def save_model(self, request: HttpRequest, obj: User, form: Any, change: bool) -> None:
        """
        Hook for intercepting the save action for the user model.
        Used to hash the password when creating a user via the admin panel and to log the action.
        """
        if "password" in form.changed_data:
            obj.set_password(form.cleaned_data["password"])
        state = {True: "updated", False: "created"}[change]
        logger.info(f"admin {state} user {obj.get_full_name()} [user_id: {obj.pk}]. data[{form.changed_data}]")
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        """
        Hook for intercepting the save action for the related user models.
        Includes account formset. Used to log the action.
        """
        for formset in formsets:
            state = {True: "updated", False: "created"}[change]
            if formset.model == Account and formset.forms and formset.forms[0].has_changed():
                logger.info(f"admin {state} account for user [user_id: {form.instance.pk}]. data[{formset.forms[0].changed_data}]")
        super().save_related(request, form, formsets, change)