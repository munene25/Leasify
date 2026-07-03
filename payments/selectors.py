
from typing import TYPE_CHECKING, Any
from django.db.models import Q, QuerySet
from django.http import QueryDict
from common.helpers import raise_not_found
from common.domain import FilteringPolicy
from payments.models import Payment
import django_filters

if TYPE_CHECKING:
    from users.models import User

BASE_QS = Payment.objects.select_related("billing__tenancy__user").all()


class PaymentFilteringPolicy(FilteringPolicy):
    SUPERUSER = Q()
    MANAGER = Q()
    CARETAKER = Q()
    TENANT = lambda u: Q(billing__tenancy__user=u)
    REGULAR = Q(pk=0)


def payment_list_for(*, user: "User", filters: dict[str, Any] | QueryDict = {}) -> QuerySet[Payment]:

    class F(django_filters.FilterSet):
        class Meta:
            model = Payment
            fields = ("billing", "status", "payment_mode")

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
def payment_get_for(*, user: "User", payment_id: int):
    u_filters = PaymentFilteringPolicy.for_user(user)
    return BASE_QS.filter(u_filters).get(pk=payment_id)

@raise_not_found("payment", "Checkout id is non existent")
def payment_get_checkout(checkout_id: str) -> Payment:
    """Get a payment by its checkout ID"""
    return Payment.objects.get(checkout_id=checkout_id)



def payment_get_extra_recepients():
    """Get additional email recepients for the users"""
    from users.models import User

    return User.objects.filter(groups__name="manager").values_list("email", flat=True)