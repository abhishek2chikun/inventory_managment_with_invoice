from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import io
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Frame
from reportlab.lib.units import inch

from datetime import datetime
def number_to_words(n):
    """Convert numbers to words (up to 999,999)."""
    ones = (
        "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"
    )
    teens = (
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
        "Sixteen", "Seventeen", "Eighteen", "Nineteen"
    )
    tens = ("Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety")
    thousands = ("", "Thousand")

    def _words(n):
        if n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            return tens[n // 10 - 2] + ('' if n % 10 == 0 else ' ' + ones[n % 10])
        elif n < 1000:
            return ones[n // 100] + ' Hundred' + ('' if n % 100 == 0 else ' and ' + _words(n % 100))
        else:
            for idx, word in enumerate(thousands):
                if n < 1000 ** (idx + 1):
                    return _words(n // (1000 ** idx)) + ' ' + word + (
                        '' if n % (1000 ** idx) == 0 else ', ' + _words(n % (1000 ** idx))
                    )

    return _words(n)


def generate_invoice_pdf(selected_products):
    # Create a bytes buffer for the PDF
    buffer = io.BytesIO()

    # Create a SimpleDocTemplate object with portrait orientation
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []

    styles = getSampleStyleSheet()
    normal_style = styles['Normal']

    # Header
    header_data = [
        ["CAPITAL AGENCIES", "", "TAX INVOICE"],
        ["Plot No. 366 & 368, Next to Dr. Agarwal Eye Hospital,", "", ""],
        ["Madhupatna, Cuttack, Odisha - 753010", "", ""],
        ["GSTIN: 21ABCDE1234F1Z9", "", ""],
        ["Invoice No: 1234", "", f"Date: {datetime.now().strftime('%Y-%m-%d')}"],
        ["Bill To: M/S GANANATH PAPERS", "", "Ship To:"],
        ["Indira Nagar, Rayagada, Odisha - 765001", "", "Indira Nagar, Rayagada, Odisha - 765001"],
        ["GSTIN: 21AABPG1234J1Z0", "", "GSTIN: 21AABPG1234J1Z0"],
    ]

    header_table = Table(header_data, colWidths=[2.5 * inch, 1.5 * inch, 2 * inch])
    header_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),  # Merge first two columns of the first row
        ('SPAN', (0, 1), (1, 1)),
        ('SPAN', (0, 2), (1, 2)),
        ('SPAN', (0, 3), (1, 3)),
        ('SPAN', (0, 4), (1, 4)),
        ('SPAN', (0, 5), (1, 5)),
        ('SPAN', (0, 6), (1, 6)),
        ('SPAN', (0, 7), (1, 7)),
        ('SPAN', (2, 5), (2, 7)),  # Merge the last column rows for Ship To
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('ALIGN', (2, 4), (2, 4), 'RIGHT'),
        ('ALIGN', (2, 5), (2, 7), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 12))

    # Product Table Header
    product_table_data = [
        ["S.No", "Item & Description", "MRP", "Per Pcs", "HSN/SAC", "Qty", "Rate", "Discount", "CGST", "SGST", "Amount"]
    ]

    # Adding the product rows
    total_amount = 0
    for idx, product in enumerate(selected_products, 1):
        amount = product['Price'] * product['Quantity']
        cgst_amount = amount * (product['CGST'] / 100)
        sgst_amount = amount * (product['SGST'] / 100)
        total = amount + cgst_amount + sgst_amount

        product_table_data.append([
            str(idx), product['Product Name'], "", "Pcs", product['HSN Code'],
            str(product['Quantity']), f"{product['Price']:.2f}", "",
            f"{product['CGST']:.2f}%", f"{product['SGST']:.2f}%", f"{total:.2f}"
        ])

        total_amount += total

    # Adding total row
    product_table_data.append(["", "", "", "", "", "", "", "", "", "Total", f"{total_amount:.2f}"])

    product_table = Table(product_table_data, colWidths=[0.5 * inch, 2.5 * inch, 0.8 * inch, 0.6 * inch, 0.8 * inch, 0.6 * inch, 1 * inch, 0.9 * inch, 0.8 * inch, 0.8 * inch, 1.2 * inch])
    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(product_table)
    elements.append(Spacer(1, 12))

    # Footer
    footer_data = [
        ["Total in Words:", f"{number_to_words(int(total_amount))} Rupees Only"],
        ["Notes:", "Thanks for your business."]
    ]

    footer_table = Table(footer_data, colWidths=[1.5 * inch, 5 * inch])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(footer_table)

    # Bank Details
    bank_details = [
        ["Bank Details: IDBI Bank, Jaypore"],
        ["Account No: 071465110004374"],
        ["IFSC: IBKL0000741"]
    ]
    bank_table = Table(bank_details, colWidths=[6.5 * inch])
    bank_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(bank_table)

    # Create the PDF
    doc.build(elements)

    # Move the buffer position to the start
    buffer.seek(0)

    return buffer

# def generate_and_download_invoice(selected_products):
#     pdf_buffer = generate_invoice_pdf(selected_products)
#     st.download_button(
#         label="Download Invoice",
#         data=pdf_buffer,
#         file_name="invoice.pdf",
#         mime="application/pdf"
#     )


# def test_generate_invoice():
#     # Dummy data for testing
#     dummy_products = [
#         {
#             'Product Name': 'Paper Ream',
#             'HSN Code': '4802',
#             'Quantity': 5,
#             'Price': 500.0,
#             'CGST': 9.0,
#             'SGST': 9.0,
#         },
#         {
#             'Product Name': 'Printer Ink',
#             'HSN Code': '8443',
#             'Quantity': 2,
#             'Price': 1500.0,
#             'CGST': 9.0,
#             'SGST': 9.0,
#         },
#         {
#             'Product Name': 'Office Chair',
#             'HSN Code': '9401',
#             'Quantity': 1,
#             'Price': 4500.0,
#             'CGST': 9.0,
#             'SGST': 9.0,
#         },
#         {
#             'Product Name': 'sPaper Ream',
#             'HSN Code': '480s2',
#             'Quantity': 5,
#             'Price': 500.0,
#             'CGST': 9.0,
#             'SGST': 9.0,
#         },
#         {
#             'Product Name': 'Pridnter Ink',
#             'HSN Code': '8443',
#             'Quantity': 2,
#             'Price': 1500.0,
#             'CGST': 9.0,
#             'SGST': 9.0,
#         },
#         {
#             'Product Name': 'Ofdfice Chair',
#             'HSN Code': '94a01',
#             'Quantity': 1,
#             'Price': 4500.0,
#             'CGST': 9.0,
#             'SGST': 9.0,
#         },
#         {
#             'Product Name': 'Papder Ream',
#             'HSN Code': '48s02',
#             'Quantity': 5,
#             'Price': 500.0,
#             'CGST': 9.0,
#             'SGST': 9.0,
#         },
#         {
#             'Product Name': 'Priednter Ink',
#             'HSN Code': '84243',
#             'Quantity': 2,
#             'Price': 1500.0,
#             'CGST': 9.0,
#             'SGST': 9.0,
#         },
#         {
#             'Product Name': 'Offwice Chair',
#             'HSN Code': '94301',
#             'Quantity': 1,
#             'Price': 4500.0,
#             'CGST': 9.0,
#             'SGST': 9.0,
#         }
#     ]
    
#     # Generate PDF with dummy data
#     generate_invoice_pdf(dummy_products, filename="test_invoice.pdf")
#     print("Invoice PDF generated successfully as 'test_invoice.pdf'.")

# Run the test function
# test_generate_invoice()