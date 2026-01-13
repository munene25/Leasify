import uuid
from rest_framework.exceptions import ValidationError
from decimal import Decimal
from .models import Payment
from tenancy.selectors import tenancy_get_by_id
from phonenumber_field.phonenumber import PhoneNumber
from django.db import transaction


class PaymentCreateService:
    def __init__(
        self,
        *,
        tenancy_id: int,
        amount: Decimal | int,
        initiator: str,
        transaction_type: str,
        phone_number: str | PhoneNumber | None = None,
        payee: str | None = None,
        tag: str | None = None,
    ) -> None:
        self.tenancy_id = tenancy_id
        self.amount = amount
        self.initiator = initiator
        self.transaction_type = transaction_type
        self.phone_number = phone_number
        self.payee = payee
        self.tag = tag

    def get_tenancy(self):
        # Need to verify tenant exists
        self.tenancy = tenancy_get_by_id(tenancy_id=self.tenancy_id)

    def verify_transaction_type(self):
        if self.transaction_type not in Payment.TransactionChoices.values:
            err = f"Transaction type '{self.transaction_type}' not valid"
            raise ValidationError({"transaction_type": [err]})

    def set_tenancy_total_paid(self):
        if isinstance(self.amount, int):
            self.amount = Decimal(self.amount)
        if isinstance(self.amount, Decimal):
            self.tenancy.total_paid = (
                self.tenancy.total_paid + self.amount
                if self.transaction_type == Payment.TransactionChoices.DEBIT
                else self.tenancy.total_paid - self.amount
            )
        else:
            err = f"Invalid amount type"
            raise ValidationError({"amount": [err]})

    def verify_total_paid_subceeds_rent(self):
        if self.tenancy.total_paid > self.tenancy.apartment.rent:
            err = f"Amount paid on apartment cannot exceed the apartment rent"
            raise ValidationError({"amount": [err]})

    def update_tenancy_total_paid(self):
        self.tenancy.save(update_fields=["total_paid"])

    def get_payee(self):
        if not self.payee:
            self.payee = self.tenancy.user.get_full_name()

    def get_phone_number(self):
        if not self.phone_number:
            self.phone_number = self.tenancy.user.phone_number
        elif isinstance(self.phone_number, str):
            self.phone_number = self._phone_number_from_string()
        else:
            err = f"Invalid phone number"
            raise ValidationError({"phone_number": [err]})

    def _phone_number_from_string(self):
        string = self.phone_number
        phone_number = PhoneNumber.from_string(phone_number=string, region="KE")
        if phone_number.is_valid():
            return phone_number
        else:
            err = f"Invalid phone number format"
            raise ValidationError({"phone_number": [err]})

    def generate_ref_no(self):
        prefix = self._get_prefix()
        tag = self.tag or self._generate_tag()
        apt_id = self.tenancy.apartment_id
        return f"{prefix}{apt_id:03}-{tag}"

    def _get_prefix(self):
        initiators = ["admin", "system", "tenant"]
        if self.initiator not in initiators:
            err = f"Initiator not allowed. Try: {initiators}"
            raise ValidationError({"initiator": [err]})
        elif self.initiator == "admin":
            return "APY"
        elif self.initiator == "tenant":
            return "TPY"
        elif self.initiator == "system":
            return "SGT"

    def _generate_tag(self):
        # Might modify later to accomodate admin prefixes to identify which admin
        return uuid.uuid4().hex[:8].upper()

    @transaction.atomic
    def create(self):
        try:
            self.get_tenancy()
            self.verify_transaction_type()
            self.set_tenancy_total_paid()
            self.verify_total_paid_subceeds_rent()
            self.get_payee()
            self.get_phone_number()

            payment = Payment(
                ref_no=self.generate_ref_no(),
                tenancy_id=self.tenancy_id,
                transaction_type=self.transaction_type,
                phone_number=self.phone_number,
                payee=self.payee,
                amount=self.amount,
            )
            payment.save()
            self.update_tenancy_total_paid()
            return payment
        except:
            raise Exception
