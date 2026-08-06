from django.contrib import admin
from django.contrib.admin.helpers import ActionForm
from django import forms
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html

from leasify.payments.models import Payment
from leasify.payments.selectors import BASE_QS
from leasify.payments.choices import PaymentMode as PM


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["pk", "billing", "tenant_name", "amount", "status", "mode"]
    list_filter = ("mode", "status")
    list_display_links = ("pk", "billing",)

    search_fields = ("tenant_name", )

    exclude = ("amount", )
    readonly_fields = ("created_at", "checkout_id", "timestamp",)

    actions = ("query_status", )
    
    def tenant_name(self, obj: Payment) -> str:
        url = reverse("admin:tenancy_tenancy_change", args=(obj.billing.tenancy.pk,))
        return format_html('<a href="{}">{}</a>', url, obj.billing.tenancy.user.full_name)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return BASE_QS

    def save_model(self, request: HttpRequest, obj: Payment, form, change) -> None:
        
        if not change:
            obj.amount = obj.billing.total_due

        if not change and obj.mode == PM.MPESA:
            from leasify.payments.services import payment_mpesa_initiate
            try:
                callback_url = request.build_absolute_uri(reverse("payments:mpesa_callback"))
                payment = payment_mpesa_initiate(
                    billing=obj.billing,
                    phone_number=obj.phone_number,
                    idempotency_key=None,
                    callback_url=callback_url,
                )
                self.message_user(request, f"Chekcout_id: {payment.checkout_id}",  level="success")
            except Exception as e:
                self.message_user(request, f"Failed: {e}", level="error")
            return None
        return super().save_model(request, obj, form, change)

    @admin.action(description="Query Payments")
    def query_status(self, request: HttpRequest, queryset: QuerySet[Payment]) -> None:
        from leasify.payments.services import payment_mpesa_query
        from leasify.payments import tasks

        success = 0
        failed = 0

        for payment in queryset:
            
            try:
                stk = payment_mpesa_query(payment=payment)
                tasks.payment_mpesa_process_async.delay(stk)
                success += 1
            except Exception as e:
                failed += 1
                self.message_user(request, f"Failed for {payment.pk}: {e}", level="error")

        if success:
            self.message_user(request, f"Successfully queried {success} payment(s).")
        if failed:
            self.message_user(request, f"Failed to queried {failed} payment(s).", level="warning")