import base64
import uuid
from pathlib import Path
from typing import Optional

import html2text
import jinja2
import pdfkit
import python_http_client.client
import sendgrid

from db.order import Order
from infrastructure import app_secrets

key_name: Optional[str] = None
api_key: Optional[str] = None


def send_cake_order_receipt(order: Order):
    client = sendgrid.SendGridAPIClient(app_secrets.sendgrid_api_key)
    # Gather email details,name,email
    from_email = sendgrid.From("anastasios.vellis@gmail.com")
    to_email = sendgrid.To(order.user.email, order.user.name)
    subject = sendgrid.Subject("Your order receipt from Cloud City Cakes")
    html = build_html('email/receipt.html', {'order': order})
    text = html2text.html2text(html)

    # Build PDF invoice
    invoice_html = build_html('email/invoice.html', {'order': order})
    pdf = build_pdf(invoice_html)

    # Attach the invoice to the email
    attachment = sendgrid.Attachment()
    attachment.file_content = pdf
    attachment.disposition = "attachment"
    attachment.file_type = "application/pdf"
    attachment.file_name = f"cloud-city-invoice-{order.id}.pdf"
    # Send email
    message = sendgrid.Mail(from_email, to_email, subject, text, html)
    message.add_attachment(attachment)
    response: python_http_client.client.Response = client.send(message)

    if response.status_code not in {200, 201, 202}:
        raise Exception(f"Error sending email: {response.status_code}")
    message = sendgrid.Mail()
    print(f"Will send email about {order} to {order.user.name}")

def build_pdf(html: str) -> str:
    # Requires install from https://wkhtmltopdf.org/ in addition to pdfkit.
    temp_file = Path(__file__).parent.parent / (str(uuid.uuid4()) + ".pdf")

    pdfkit.from_string(html, str(temp_file))
    pdf_bytes = temp_file.read_bytes()

    temp_file.unlink()

    encoded_pdf = base64.b64encode(pdf_bytes).decode('ascii')
    return encoded_pdf

def build_html(template_file: str, data: dict) -> str:
    template_folder = str(Path(__file__).parent.parent / "templates")
    loader = jinja2.FileSystemLoader(template_folder)
    env = jinja2.Environment(loader=loader)

    template: jinja2.Template = loader.load(env, template_file, None)
    html = template.render(**data)

    return html
