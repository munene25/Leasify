from structlog import get_logger
from django.contrib import admin
from django.db import transaction
from billing.models import BillingPeriod as BP
from billing.choices import BillingStatus as BS
from django.urls import reverse
from django.utils.html import format_html
from billing.services import billing_period_cancel
from datetime import date
logger = get_logger("tenancy.admin")



@admin.register(BP)
class BillingPeriodAdmin(admin.ModelAdmin):
    list_display = ("pk", "tenant", "start_date", "is_current", "total_due", "status")
    list_filter = ("status",)
    

    fields = (
        "tenancy",
        "start_date",
        "end_date",
        "created_at",
        "total_due",
        "status",
        "duration_months",
    )
    def tenant(self, obj: BP) -> str:
        url = reverse("admin:tenancy_tenancy_change", args=(obj.tenancy.pk,))
        return format_html(f'<a href="{url}">{obj.tenancy.user.full_name}</a>')

    def duration_months(self, obj: BP) -> int:
        return obj.duration_months

    def next_start(self, obj: BP) -> date:
        return obj.next_start
    
    def is_current(self, obj) -> bool:
        return obj.is_current

    is_current.boolean = True
    is_current.short_description = "Covers this month"


    readonly_fields = ("created_at",)
    actions = ["cancel",]

    @admin.action(description="Cancel selected billing periods")
    @transaction.atomic
    def cancel(self, request, queryset) -> None:
        for billing in queryset.all():
            if billing.status == BS.UNPAID:
                billing_period_cancel(billing)
