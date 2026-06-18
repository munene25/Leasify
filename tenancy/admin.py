from structlog import get_logger
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from tenancy.models import Tenancy
from django.urls import reverse
from django.utils.html import format_html
from tenancy.selectors import BASE_QS

logger = get_logger("tenancy.admin")


@admin.register(Tenancy)
class TenancyAdmin(admin.ModelAdmin):
    list_display = ("pk", "apartment_name", "tenant_name", "status", "billings")
    list_filter = ("status", "termination_reason")

    search_fields = (
        "tenant__user__first_name",
        "tenant__user__last_name",
        "apartment__unit_number",
        "apartment__block__name",
    )

    fields = (
        "apartment",
        "user",
        "status",
        "created_at",
        "reservation_expiry",
        "termination_reason",
        "termination_date",
    )
    readonly_fields = ("created_at", "reservation_expiry")
    actions = ["terminate",]
    
    def tenant_name(self, obj):
        url = reverse("admin:users_user_change", args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.full_name)

    def apartment_name(self, obj):
        url = reverse("admin:apartments_apartment_change", args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.apartment.name)

    def billings(self, obj):
        url = reverse("admin:billing_billingperiod_changelist")
        # Filter by tenancy
        url = f"{url}?tenancy__id__exact={obj.pk}"
        return format_html('<a href="{}">view billings</a>', url)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return BASE_QS
