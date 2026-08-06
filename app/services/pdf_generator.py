import os
import tempfile
import urllib.request
from fpdf import FPDF
from datetime import datetime
from PIL import Image as PILImage

STATUS_LABELS = {
    "pending": "Pendiente",
    "accepted": "Aceptado",
    "rejected": "Rechazado",
}

FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")


def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = (hex_color or "#4f46e5").lstrip("#")
    if len(hex_color) != 6:
        return (79, 70, 229)
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return (79, 70, 229)


def _format_currency(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def _download_logo(url: str) -> str | None:
    try:
        ext = os.path.splitext(url.split("?")[0])[-1] or ".png"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.close()
        urllib.request.urlretrieve(url, tmp.name)
        return tmp.name
    except Exception as e:
        print(f"[PDF] Error descargando logo: {e}")
        return None


def _setup_fonts(pdf: FPDF) -> bool:
    regular = os.path.join(FONTS_DIR, "Roboto-Regular.ttf")
    bold    = os.path.join(FONTS_DIR, "Roboto-Bold.ttf")
    italic  = os.path.join(FONTS_DIR, "Roboto-Italic.ttf")
    if all(os.path.exists(f) for f in [regular, bold, italic]):
        pdf.add_font("Roboto", "",  regular)
        pdf.add_font("Roboto", "B", bold)
        pdf.add_font("Roboto", "I", italic)
        return True
    return False


class PresuPDF(FPDF):
    """FPDF con footer automático — evita que set_y(-N) dispare un page break."""

    def __init__(self, font: str, primary: tuple, user_name: str):
        super().__init__()
        self._font = font
        self._primary = primary
        self._user_name = user_name

    def footer(self):
        self.set_y(-14)  # siempre a 14mm del borde inferior
        self.set_draw_color(*self._primary)
        self.set_line_width(0.3)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(1)
        self.set_font(self._font, "I", 7)
        self.set_text_color(107, 114, 128)
        self.cell(0, 5, f"Generado por PresuApp  ·  {self._user_name}", align="C")


def generate_budget_pdf(budget, user, client) -> bytes:
    is_pro = getattr(user, "plan", "free") == "pro"
    # Free: color genérico, sin logo. Pro: color y logo propios.
    PRIMARY = _hex_to_rgb(user.pdf_color if is_pro else "#4f46e5")
    WHITE      = (255, 255, 255)
    GRAY_DARK  = (31, 41, 55)
    GRAY_MID   = (107, 114, 128)
    GRAY_LIGHT = (243, 244, 246)

    pdf = PresuPDF(font="Helvetica", primary=PRIMARY, user_name=user.name)
    pdf.set_margins(20, 20, 20)
    # Reservar 14mm para el footer — evita page-break automático en ese área
    pdf.set_auto_page_break(auto=True, margin=14)

    use_roboto = _setup_fonts(pdf)
    FONT = "Roboto" if use_roboto else "Helvetica"
    pdf._font = FONT  # actualiza la subclase

    pdf.add_page()

    logo_path = None

    # ── ENCABEZADO ───────────────────────────────────────────
    HDR_H = 38
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(0, 0, 210, HDR_H, "F")

    # Logo — izquierda, máximo 42×28mm manteniendo proporción (solo Pro)
    LOGO_MAX_W, LOGO_MAX_H = 42, 28
    if is_pro and user.logo_url:
        logo_path = _download_logo(user.logo_url)
        if logo_path:
            try:
                pil = PILImage.open(logo_path)
                img_w, img_h = pil.size
                pil.close()

                if img_h == 0:
                    raise ValueError("Imagen con alto 0")

                aspect = img_w / img_h
                if aspect >= LOGO_MAX_W / LOGO_MAX_H:  # más ancho que el box
                    logo_w = LOGO_MAX_W
                    logo_h = round(LOGO_MAX_W / aspect, 2)
                else:                                    # más alto que el box
                    logo_h = LOGO_MAX_H
                    logo_w = round(LOGO_MAX_H * aspect, 2)

                logo_y = round((HDR_H - logo_h) / 2, 2)
                pdf.image(logo_path, x=14, y=logo_y, w=logo_w, h=logo_h)
            except Exception as e:
                print(f"[PDF] Error cargando logo: {e}")
                logo_path = None

    # Info del negocio — derecha, alineada a la derecha del header
    # Usamos x=20, ancho=170 con align="R" para pegar contra el margen derecho
    pdf.set_text_color(*WHITE)
    pdf.set_font(FONT, "B", 15)
    pdf.set_xy(20, 7)
    pdf.cell(170, 7, user.business_name or user.name, align="R", ln=True)

    contact_parts = [p for p in [user.address, user.city, user.phone] if p]
    pdf.set_font(FONT, "", 7.5)
    if contact_parts:
        pdf.set_xy(20, 17)
        pdf.cell(170, 4, "  |  ".join(contact_parts), align="R", ln=True)
    pdf.set_xy(20, 23)
    pdf.cell(170, 4, user.email or "", align="R", ln=True)

    # ── TÍTULO DEL PRESUPUESTO ───────────────────────────────
    pdf.set_text_color(*GRAY_DARK)
    pdf.set_y(HDR_H + 5)
    pdf.set_font(FONT, "B", 13)
    pdf.cell(0, 7, f"PRESUPUESTO #{budget.number:04d}", ln=True)

    pdf.set_font(FONT, "", 8)
    pdf.set_text_color(*GRAY_MID)
    fecha = datetime.fromisoformat(str(budget.created_at)).strftime("%d/%m/%Y")
    estado = STATUS_LABELS.get(budget.status, budget.status)
    pdf.cell(100, 4.5, f"Fecha: {fecha}")
    pdf.cell(0, 4.5, f"Estado: {estado}", ln=True)

    if budget.valid_until:
        venc = datetime.fromisoformat(str(budget.valid_until)).strftime("%d/%m/%Y")
        pdf.cell(0, 4, f"Válido hasta: {venc}", ln=True)

    pdf.ln(3)

    # ── CLIENTE ──────────────────────────────────────────────
    if client:
        pdf.set_fill_color(*GRAY_LIGHT)
        pdf.set_text_color(*GRAY_DARK)
        pdf.set_font(FONT, "B", 7.5)
        pdf.cell(0, 5.5, "  CLIENTE", fill=True, ln=True)
        pdf.set_font(FONT, "", 8)
        lines = [client.name]
        if client.email:   lines.append(client.email)
        if client.phone:   lines.append(client.phone)
        if client.address: lines.append(client.address)
        for line in lines:
            pdf.cell(0, 4.5, f"  {line}", ln=True)
        pdf.ln(3)

    # ── DESCRIPCIÓN ──────────────────────────────────────────
    if budget.description:
        pdf.set_font(FONT, "I", 8)
        pdf.set_text_color(*GRAY_MID)
        pdf.multi_cell(0, 4.5, budget.description)
        pdf.ln(2)

    # ── TABLA ────────────────────────────────────────────────
    col_desc  = 90
    col_qty   = 20
    col_price = 35
    col_sub   = 35

    pdf.set_fill_color(*PRIMARY)
    pdf.set_text_color(*WHITE)
    pdf.set_font(FONT, "B", 8)
    pdf.cell(col_desc,  6.5, "  Descripción", fill=True)
    pdf.cell(col_qty,   6.5, "Cant.",          align="C", fill=True)
    pdf.cell(col_price, 6.5, "Precio unit.",   align="R", fill=True)
    pdf.cell(col_sub,   6.5, "Subtotal",       align="R", fill=True)
    pdf.ln()

    pdf.set_text_color(*GRAY_DARK)
    pdf.set_font(FONT, "", 8)
    alt = False
    for item in budget.budget_items:
        pdf.set_fill_color(*(GRAY_LIGHT if alt else WHITE))

        y_start = pdf.get_y()

        # Descripción con wrap automático (multi_cell avanza Y)
        pdf.set_x(20)
        pdf.multi_cell(col_desc, 5.5, f"  {item.description}", fill=True)
        y_end = pdf.get_y()
        row_h = y_end - y_start

        # Las otras celdas usan la altura total de la fila
        pdf.set_xy(20 + col_desc, y_start)
        pdf.cell(col_qty,   row_h, str(item.quantity),                align="C", fill=True)
        pdf.cell(col_price, row_h, _format_currency(item.unit_price), align="R", fill=True)
        pdf.cell(col_sub,   row_h, _format_currency(item.subtotal),   align="R", fill=True)
        pdf.set_xy(20, y_end)

        alt = not alt

    # Línea separadora
    pdf.set_draw_color(*PRIMARY)
    pdf.set_line_width(0.4)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(2.5)

    # ── TOTALES ──────────────────────────────────────────────
    tx = 120
    pdf.set_text_color(*GRAY_MID)
    pdf.set_font(FONT, "", 8)
    pdf.set_x(tx)
    pdf.cell(35, 5, "Subtotal:", align="R")
    pdf.cell(35, 5, _format_currency(budget.subtotal), align="R", ln=True)

    if budget.discount_percent and budget.discount_percent > 0:
        pdf.set_text_color(22, 163, 74)  # verde
        pdf.set_x(tx)
        pdf.cell(35, 5, f"Descuento ({budget.discount_percent:.0f}%):", align="R")
        pdf.cell(35, 5, f"- {_format_currency(budget.discount_amount)}", align="R", ln=True)
        pdf.set_text_color(*GRAY_MID)

    if budget.tax_percent and budget.tax_percent > 0:
        pdf.set_x(tx)
        pdf.cell(35, 5, f"IVA ({budget.tax_percent:.0f}%):", align="R")
        pdf.cell(35, 5, _format_currency(budget.tax_amount), align="R", ln=True)

    pdf.set_font(FONT, "B", 11)
    pdf.set_text_color(*PRIMARY)
    pdf.set_x(tx)
    pdf.cell(35, 7, "TOTAL:", align="R")
    pdf.cell(35, 7, _format_currency(budget.total), align="R", ln=True)

    # ── NOTAS ────────────────────────────────────────────────
    if budget.notes:
        pdf.ln(4)
        pdf.set_font(FONT, "B", 7.5)
        pdf.set_text_color(*GRAY_MID)
        pdf.cell(0, 4.5, "Notas y condiciones:", ln=True)
        pdf.set_font(FONT, "", 8)
        pdf.multi_cell(0, 4.5, budget.notes)

    # Limpieza logo temporal
    if logo_path and os.path.exists(logo_path):
        os.unlink(logo_path)

    return bytes(pdf.output())
