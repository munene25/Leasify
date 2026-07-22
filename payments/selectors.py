from typing import Any
from django.db.models import Q, QuerySet
from django.http import QueryDict
from common.helpers import raise_not_found
from common.domain import FilteringPolicy
from users.models import User
from payments.models import Payment
import django_filters

BASE_QS = Payment.objects.select_related("billing__tenancy__user")


class PaymentFilteringPolicy(FilteringPolicy):
    SUPERUSER = Q()
    MANAGER = Q()
    CARETAKER = Q()
    TENANT = lambda u: Q(billing__tenancy__user=u)
    REGULAR = Q(pk=0)


def payment_list_for(*, user: User, filters: dict[str, Any] | QueryDict = {}) -> QuerySet[Payment]:
    """
    Retrieves a list of payments for the given user with optional filtering.

    Returns all payments viewable by the user.

    :param user: The authenticated user viewing the payments
    :param filters: Optional dictionary of filter parameters or query dict
    :return: A QuerySet containing Payment objects visible by the given user and filters
    """

    class F(django_filters.FilterSet):
        class Meta:
            model = Payment
            fields = ("billing", "status", "mode")

        search = django_filters.CharFilter(method="search_fields")

        def search_fields(self, queryset, name, value):
            return queryset.filter(
                Q(checkout_id__icontains=value)
                | Q(phone_number__icontains=value)
                | Q(receipt_no__icontains=value)
                | Q(recorded_by__first_name__istartswith=value)
                | Q(recorded_by__last_name__istartswith=value)
                | Q(billing__tenancy__user__first_name__istartswith=value)
                | Q(billing__tenancy__user__last_name__istartswith=value)
            ).distinct()

    u_filters = PaymentFilteringPolicy.for_user(user)
    qs = BASE_QS.filter(u_filters)
    return F(filters, qs).qs


@raise_not_found("payment", "Payment not found")
def payment_get_for(*, user: User, payment_id: int) -> Payment:
    """Retrieves a specific payment by its ID for the given user.

    Returns a single Payment object matching both the provided `payment_id` and the authenticated user's permissions. If no matching payment is found, a 404 error will be raised.

    :param user: The authenticated user whose payments are being retrieved
    :param payment_id: The primary key of the payment to retrieve
    :return: A Payment object matching the given ID for the provided user
    """

    u_filters = PaymentFilteringPolicy.for_user(user)
    return BASE_QS.filter(u_filters).get(pk=payment_id)


@raise_not_found("checkout_id", "Payment with checkout_id does not exist")
def payment_get_checkout(checkout_id: str) -> Payment:
    """Retrieves a specific payment by its checkout ID.

    Returns a single Payment object matching the provided `checkout_id`. If no matching payment is found, a 404 error will be raised.

    :param checkout_id: The checkout identifier to search for
    :return: A Payment object with the given checkout ID
    """
    return Payment.objects.get(checkout_id=checkout_id)


def payment_get_extra_recipients() -> list[str]:
    """Retrieves a list of additional email recipients for payment notifications.

    Returns the email addresses of all users with the "manager" group, used to notify them about payments.

    :return: A list of email address strings
    """
    emails = User.objects.filter(groups__name="manager").values_list("email", flat=True).all()
    return list(emails)
