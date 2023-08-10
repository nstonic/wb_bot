import os
import pathlib
from base64 import b64decode
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image as PILImage
from django.conf import settings
from reportlab.graphics.barcode import code128
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, PageTemplate, NextPageTemplate
from reportlab.platypus import Image, Frame, PageBreak
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table

from wb_api.models import Order, Product, OrderQRCode, SupplyQRCode


def get_supply_sticker(supply_qr_code: SupplyQRCode) -> bytes:
    sticker_in_bytes = b64decode(
        supply_qr_code.image_string,
        validate=True
    )
    with BytesIO(sticker_in_bytes) as file:
        image = PILImage.open(file).rotate(-90, expand=True)
    with BytesIO() as file:
        image.save(file, format='PNG')
        supply_sticker = file.getvalue()
    return supply_sticker


def get_orders_stickers(
        orders: list[Order],
        products: list[Product],
        qr_codes: list[OrderQRCode],
        supply_id: str
) -> BytesIO:
    articles = set(order.article for order in orders)
    sticker_files = []
    for article in articles:
        orders_with_same_article = [
            order.id
            for order in orders
            if order.article == article
        ]
        product = next(
            filter(
                lambda p: p.article == article,
                products
            )
        )
        orders_qr_codes = [
            qr_code
            for qr_code in qr_codes
            if qr_code.order_id in orders_with_same_article
        ]
        sticker_file = create_stickers_by_article(
            product,
            orders_qr_codes
        )
        sticker_files.append(sticker_file)

    zip_file = BytesIO()
    zip_file.name = f'Stickers for {supply_id}.zip'
    with ZipFile(zip_file, 'a', ZIP_DEFLATED, False) as archive:
        for sticker_file in sticker_files:
            archive.writestr(sticker_file.name, sticker_file.getvalue())
            sticker_file.close()
    return zip_file


def create_stickers_by_article(
        product: Product,
        qr_codes: list[OrderQRCode]
) -> BytesIO:
    order_qr_code_files = []
    for qr_code in qr_codes:
        qr_code_in_byte_format = b64decode(
            qr_code.file,
            validate=True
        )
        order_qr_code_files.append(
            BytesIO(qr_code_in_byte_format)
        )
    pdf_file = BytesIO()
    pdf_file.name = f'{product.article}.pdf'
    pdf = BaseDocTemplate(pdf_file, showBoundary=0)

    font_path = os.path.join(pathlib.Path(__file__).parent.resolve(), settings.BOT_BARCODE_FONT_FILE)
    pdfmetrics.registerFont(TTFont(settings.BOT_BARCODE_FONT_NAME, font_path))
    sticker_size = (120 * mm, 75 * mm)
    style = getSampleStyleSheet()['BodyText']
    style.fontName = settings.BOT_BARCODE_FONT_NAME
    style.fontSize = 9.5
    style.leading = 10
    frame_sticker = Frame(0, 0, *sticker_size)
    frame_description = Frame(10 * mm, 5 * mm, 100 * mm, 40 * mm, topPadding=0)

    elements = []
    for qr_code in order_qr_code_files:
        colors = ', '.join(product.colors)
        countries = ', '.join(product.countries)
        data = [
            [Paragraph(product.name, style)],
            [Paragraph(f'Артикул: {product.article}', style)],
            [Paragraph(f'Страна: {countries}', style)],
            [Paragraph(f'Бренд: {product.brand}', style)],
        ]
        if colors:
            data.append([Paragraph(f'Цвет: {colors}', style)])

        elements.append(Image(qr_code, useDPI=300, width=95 * mm, height=65 * mm))
        elements.append(NextPageTemplate('Barcode'))
        elements.append(PageBreak())
        elements.append(Table(data, colWidths=[100 * mm]))
        elements.append(NextPageTemplate('Image'))
        elements.append(PageBreak())

        def barcode(canvas, doc):
            canvas.saveState()
            barcode128 = code128.Code128(
                product.barcode,
                barHeight=50,
                barWidth=1.45,
                humanReadable=True
            )
            barcode128.drawOn(canvas, x=19.5 * mm, y=53 * mm)
            canvas.restoreState()

        pdf.addPageTemplates(
            [PageTemplate(id='Image', frames=frame_sticker, pagesize=sticker_size),
             PageTemplate(id='Barcode', frames=frame_description, pagesize=sticker_size, onPage=barcode)]
        )
    pdf.build(elements)
    return pdf_file
