from decimal import Decimal
from payments.models import Payment
from payments.services import PaymentCreateService
from tenancy.selectors import tenancy_get_by_id


class TenancyDeleteService:
    def __init__(self, tenancy_id):
        self.tenancy_id = tenancy_id

    def _get_tenancy(self):
        self.tenancy = tenancy_get_by_id(tenancy_id=self.tenancy_id)

    def _credit_payments(self):
        PaymentCreateService(
            amount=self.tenancy.total_paid,
            transaction_type="credit",
            tenancy_id=self.tenancy_id,
            initiator="system",
        ).create()

    def _set_apartment_available(self):
        pass

    def delete(self):
        self._get_tenancy()
        self._credit_payments()
        # skipped making apartment available
        # self._set_apartment_available()
        self.tenancy.delete()
