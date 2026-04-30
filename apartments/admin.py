from structlog import get_logger
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from apartments.models import Apartment
from django.urls import reverse
from django.utils.html import format_html

logger = get_logger("apartments.admin")


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = ("apartment_name", "rentable", "rent", "is_occupied")
    list_filter = ("rentable", "block")

    search_fields = ("unit_number",)

    fields = (
        "block",
        "unit_number",
        "rentable",
        "rent",
        "is_occupied",
        "created_at",
        "current_tenant",
    )

    readonly_fields = ("is_occupied", "current_tenant", "created_at")
    actions = ["make_rentable", "make_unrentable"]

    def is_occupied(self, obj):
        return obj.is_occupied

    is_occupied.boolean = True
    is_occupied.short_description = "Currently is_occupied"

    def current_tenant(self, obj):
        tenant = obj.current_tenant

        if not tenant:
            return "--/--"

        url = reverse("admin:users_user_change", args=[tenant.pk])

        return format_html('<a href="{}">{}</a>', url, tenant.user.full_name)
    
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        from apartments.selectors import tenancy_prefetch

        return super().get_queryset(request).prefetch_related(tenancy_prefetch())

    @admin.action(description="Mark selected apartments as rentable")
    def make_rentable(self, request, queryset):
        queryset.update(rentable=True)
        logger.info("apartments_made_rentable", apartments=queryset.value_list("id", flat=True))
    
    @admin.action(description="Mark selected apartments as not renatble")
    def make_unrentable(self, request, queryset):
        queryset.update(rentable=False)
        logger.info("apartments_made_unrentable", apartments=queryset.value_list("id", flat=True))

    def save_model(self, request, obj, form, change) -> None:
        super().save_model(request, obj, form, change)
        state = {True: "apartment_updated", False: "apartment_created"}[change]
        logger.info(state, apartment_name=obj.apartment_name)

    def delete_model(self, request: HttpRequest, obj) -> None:
        super().delete_model(request, obj)
        logger.warning("apartment_deleted", apartment_name=obj.apartment_name)
    