from datetime import date

from django.contrib import admin
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html

from leasify.billing.services import billing_period_cancel
from leasify.billing.models import BillingPeriod as BP
from leasify.billing.choices import BillingStatus as BS



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
    )

    readonly_fields = (
        "created_at",
        "total_due",
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

    def save_model(self, request, obj: BP, form, change) -> None:
        from leasify.common.period import DateRange

        if "start_date" in form.cleaned_data or "end_date" in form.cleaned_data:
            r = DateRange(obj.start_date, obj.end_date)
            obj.start_date = r.start_date
            obj.end_date = r.end_date
            obj.total_due = obj.tenancy.apartment.rent * obj.duration_months

        super().save_model(request, obj, form, change)