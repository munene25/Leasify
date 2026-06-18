from io import BytesIO
from weasyprint import HTML
from django.template.loader import render_to_string
from payments.models import PaymentStatus, Payment
from config.emails import send_template_email

def generate_payment_receipt_pdf(payment) -> bytes:
    """Generate a PDF receipt from payment using WeasyPrint."""

    # Render template to HTML string using Django's render_to_string helper
    html_content = render_to_string("payments/receipt.html", {"payment": payment})

    # Convert HTML to PDF using WeasyPrint
    buffer = BytesIO()
    HTML(string=html_content).write_pdf(buffer)
    return buffer.getvalue()


def notify_payment_received(payment_id: int):
    """Send payment receipt email to the user with PDF attachment."""

    payment = Payment.objects.select_related("billing__tenancy__user", "billing__tenancy__apartment", "billing").get(pk=payment_id)
    user = payment.billing.tenancy.user

    # Generate PDF content
    pdf_content = generate_payment_receipt_pdf(payment)

    context = {
        "received_from": user.full_name,
        "receipt_no": payment.receipt_no or "N/A",
        "payment": payment,
        "status": "SUCCESS" if payment.status == PaymentStatus.SUCCESS else "FAILED",
        "receipt_date": payment.created_at.strftime("%d %b %Y, %I:%M %p"),
    }
    # ? Also send to the maager/caretaker etc
    # ? In order to do so the email should be as generic as possible.
    send_template_email(
        subject="Payment received",
        context=context,
        to=[user.email], 
        template_name="emails/payment_notification",
        attachment=pdf_content,
        attachment_name=f"PaymentReceipt[{payment.billing.name}]",
        attachment_type="application/pdf",
    )


def generate_payment_receipt_for_download(payment):
    """Generate a PDF receipt and return it for download."""

    # Generate the PDF (returns bytes)
    pdf_content = generate_payment_receipt_pdf(payment)

    return pdf_content
