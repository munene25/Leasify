from typing import Any
from structlog import get_logger
from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.models import BaseUserManager
from django.http import HttpRequest
from users.models import User, Account


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
    group = forms.ChoiceField(choices=[], help_text="Select a group to assign to the user to.", label="Group")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        group_field = self.fields["group"]
        group_choices = [("none", "None")]
        initial = "none"

        for group in Group.objects.all():
            if self.instance and self.instance.groups.first() == group:
                initial = group.name
            group_choices.append((group.name, group.name.capitalize()))

        group_field.choices = group_choices
        group_field.initial = initial

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
    exclude = ("created_at",)
    fk_name = "user"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "is_staff", "is_superuser", "is_active", "phone_number")
    list_select_related = ("account",)
    search_fields = ("email", "first_name", "last_name")
    list_filter = ("is_active", "is_staff", "is_superuser",)

    form = UserAdminForm
    exclude = ("last_login", "created_at", "last_email_change", "groups")
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

        state = {True: "user_updated", False: "user_created"}[change]
        super().save_model(request, obj, form, change)
        logger.info(state, target_id=obj.pk, email=obj.email)

    def save_related(self, request, form, formsets, change):
        """
        Hook for intercepting the save action for the related user models.
        Includes account formset. Used to log the action.
        """
        if "group" in form.changed_data:
            from users.services import user_set_role, user_remove_role

            user, role = form.instance, form.cleaned_data.get("group")
            if role is "none":
                user_remove_role(user)
            else:
                group = Group.objects.get(name=role)
                user_set_role(user=user, role=group, replace=True)

        state = {True: "updated", False: "created"}[change]
        for formset in formsets:
            if formset.has_changed():
                changed = [fset_form.changed_data for fset_form in formset]
                event = formset.model.__name__ + "_" + {state}
                logger.info(event, target_id=form.instance.pk, fields=changed)
        super().save_related(request, form, formsets, change)
