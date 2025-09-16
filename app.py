from flask import Flask, render_template, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from zoneinfo import ZoneInfo
import io,datetime
import os


app = Flask(__name__)

# ✅ Cấu hình sản phẩm và giá theo số lượng
PRODUCTS = {
    "KDG XÁM PHỔ THÔNG": {
        "price_tiers": [(100, 125000), (50, 140000), (20, 145000), (10, 150000)],
        "market_price": 195000,
        "base_commission": 8000
    },
    "KDG TRẮNG PHỔ THÔNG": {
        "price_tiers": [(100, 140000), (50, 155000), (20, 160000), (10, 165000)],
        "market_price": 250000,
        "base_commission": 15000
    },
    "KDG XÁM EXTRA": {
        "price_tiers": [(100, 170000), (50, 180000), (20, 190000), (10, 195000)],
        "market_price": 295000,
        "base_commission": 15000
    },
    "KDG TRẮNG EXTRA": {
        "price_tiers": [(100, 200000), (50, 210000), (20, 220000), (10, 225000)],
        "market_price": 350000,
        "base_commission": 15000
    },
    "KCR TRẮNG PHỔ THÔNG (BỊCH)": {
        "price_tiers": [(40, 230000), (10, 265000), (5, 290000)],
        "market_price": 336000,
        "base_commission": 15000
    },
    "KCR TRẮNG EXTRA (BỊCH)": {
        "price_tiers": [
            (40, 300000),
            (10, 336000),
            (5, 360000)
        ],
        "market_price": 408000,
        "base_commission": 30000
    },
    "KCR TRẮNG HỘP": {
        "price_tiers": [
            (30, 285000),
            (10, 345000),
            (5, 375000)
        ],
        "market_price": 484000,
        "base_commission": 10000
    }
}

def get_price(product, quantity):
    tiers = PRODUCTS.get(product, {}).get("price_tiers", [])
    for min_qty, price in tiers:
        if quantity >= min_qty:
            return price
    return 0

def get_market_price(product):
    return PRODUCTS.get(product, {}).get("market_price", 0)

def get_base_commission(product):
    return PRODUCTS.get(product, {}).get("base_commission", 0)

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    total_commission = 0
    product_results = []

    if request.method == 'POST':
        # Lấy danh sách sản phẩm, số lượng bán và tặng từ form
        products = request.form.getlist('product[]')
        sell_quantities = request.form.getlist('sell_qty[]')
        gift_quantities = request.form.getlist('gift_qty[]')

        # Kiểm tra dữ liệu đầu vào
        if not products or not sell_quantities or not gift_quantities:
            return render_template('index.html', result={'error': 'Vui lòng chọn ít nhất một sản phẩm và nhập số lượng.'})

        for i, (product, sell_qty, gift_qty) in enumerate(zip(products, sell_quantities, gift_quantities)):
            try:
                sell_qty = int(sell_qty)
                gift_qty = int(gift_qty)
            except ValueError:
                return render_template('index.html', result={'error': 'Số lượng phải là số nguyên.'})

            # Nếu là sản phẩm KCR thì cho phép từ 5 trở lên, các loại khác từ 10
            if "KCR" in product:
                min_qty = 5
            else:
                min_qty = 10

            if sell_qty < min_qty:
                return render_template('index.html',
                                       result={'error': f'Số lượng bán của {product} phải từ {min_qty} trở lên.'})

            total_qty = sell_qty + gift_qty
            G = get_price(product, sell_qty)
            D = get_market_price(product)

            if total_qty <= 0:
                return render_template('index.html', result={'error': f'Tổng số lượng của {product} phải lớn hơn 0.'})

            after_gift_price = (D * sell_qty) / total_qty
            approved = after_gift_price >= G

            product_result = {
                'product': product,
                'sell_qty': sell_qty,
                'gift_qty': gift_qty,
                'G': G,
                'D': D,
                'after_gift_price': after_gift_price,
                'approved': approved
            }

            if approved and 'gift_value[]' in request.form:
                gift_values = request.form.getlist('gift_value[]')
                try:
                    gift_value = int(gift_values[i])
                except (ValueError, IndexError):
                    return render_template('index.html', result={'error': f'Giá trị quà của {product} không hợp lệ.'})

                fund = (after_gift_price - G) * total_qty
                base_commission = get_base_commission(product)
                company_commission = base_commission * sell_qty
                bonus = fund - gift_value
                commission = bonus + company_commission
                total_commission += commission

                product_result['commission_data'] = {
                    'fund': fund,
                    'gift_value': gift_value,
                    'bonus': bonus,
                    'total_commission': commission
                }

            product_results.append(product_result)

        result = {
            'products': product_results,
            'total_commission': total_commission
        }

    return render_template('index.html', result=result)

# Đăng ký font Unicode
font_path = "DejaVuSans.ttf"
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont("DejaVu", font_path))
else:
    raise FileNotFoundError("Thiếu file font DejaVuSans.ttf trong thư mục")

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    products = request.form.getlist('product[]')
    sell_quantities = request.form.getlist('sell_qty[]')
    gift_quantities = request.form.getlist('gift_qty[]')
    after_gift_prices = request.form.getlist('after_gift_price[]')
    approved_list = request.form.getlist('approved[]')
    gift_values = request.form.getlist('gift_value[]')
    funds = request.form.getlist('fund[]')
    total_commission = request.form.get('total_commission', '0')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", fontName="DejaVu", fontSize=18, alignment=1, spaceAfter=20))
    styles.add(ParagraphStyle(name="NormalVN", fontName="DejaVu", fontSize=11, leading=14))
    styles.add(ParagraphStyle(name="RightSmall", fontName="DejaVu", fontSize=9, alignment=2, textColor=colors.grey))
    styles.add(ParagraphStyle(name="RightBold", fontName="DejaVu", fontSize=11, alignment=2))

    # ✅ style cho cell để tự xuống dòng
    style_cell = ParagraphStyle(
        name="CellStyle",
        fontName="DejaVu",
        fontSize=10,
        leading=12,
        alignment=0,     # căn trái để xuống dòng
        wordWrap='CJK'   # tự động xuống dòng
    )

    story = []

    # 🔹 Header: Logo + Ngày xuất báo cáo
    logo_path = os.path.join(app.root_path, "static", "logo.png")
    try:
        logo = Image(logo_path, width=5.1*cm, height=1*cm)
    except:
        logo = Paragraph("", styles["NormalVN"])

    today = datetime.datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y %H:%M")
    header_data = [[logo, Paragraph(f"Ngày xuất báo cáo: {today}", styles["RightSmall"])]]
    header_table = Table(header_data, colWidths=[4*cm, 12*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # 🔹 Tiêu đề
    story.append(Paragraph("BÁO CÁO HOA HỒNG", styles["CenterTitle"]))
    story.append(Spacer(1, 12))

    # 🔹 Dữ liệu bảng
    headers = ["Sản phẩm", "SL Bán", "SL Tặng", "Giá sau tặng",
               "Trạng thái", "Quỹ quà tặng", "GT quà tặng", "Hoa hồng SP"]

    data = [[Paragraph(h, style_cell) for h in headers]]
    total_commission_all = 0

    for i, product in enumerate(products):
        try:
            sell_qty = int(sell_quantities[i])
            gift_qty = int(gift_quantities[i])
            total_qty = sell_qty + gift_qty
            D = float(get_market_price(product))
            G = float(get_price(product, sell_qty))
            base_commission = get_base_commission(product)

            F = (D * sell_qty) / total_qty if total_qty > 0 else 0
            fund_val = (F - G) * total_qty
            try:
                gift_val = float(gift_values[i])
            except:
                gift_val = 0

            commission_company = base_commission * sell_qty
            commission_product = (fund_val - gift_val) + commission_company
            total_commission_all += commission_product

            price = "{:,.0f}₫".format(F)
            fund_str = "{:,.0f}₫".format(fund_val)
            gift_str = "{:,.0f}₫".format(gift_val)
            commission_str = "{:,.0f}₫".format(commission_product)
            status = "DUYỆT" if approved_list[i] == "True" else "KHÔNG DUYỆT"

            data.append([
                Paragraph(product, style_cell),
                Paragraph(str(sell_qty), style_cell),
                Paragraph(str(gift_qty), style_cell),
                Paragraph(price, style_cell),
                Paragraph(status, style_cell),
                Paragraph(fund_str, style_cell),
                Paragraph(gift_str, style_cell),
                Paragraph(commission_str, style_cell)
            ])

        except Exception as e:
            print("Lỗi:", e)

    # Thêm dòng tổng hoa hồng ngay trong bảng
    data.append([
        Paragraph("<b>TỔNG HOA HỒNG</b>", style_cell),
        "", "", "", "", "", "",
        Paragraph(f"<b>{total_commission_all:,.0f}₫</b>", style_cell)
    ])

    # 🔹 Bảng chính
    col_widths = [3*cm, 2*cm, 2*cm, 2.2*cm, 2*cm, 3*cm, 3*cm, 3*cm]
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#d8e806")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'DejaVu'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.whitesmoke, colors.lightgrey]),

        # ✅ Dòng tổng hoa hồng
        ('SPAN', (0,-1), (-2,-1)),  # gộp 7 cột đầu
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
        ('ALIGN', (0,-1), (-1,-1), 'CENTER'),  # căn giữa cả dòng tổng
        ('FONTNAME', (0,-1), (-1,-1), 'DejaVu'),
        ('FONTSIZE', (0,-1), (-1,-1), 12),
    ]))
    story.append(table)
    story.append(Spacer(1, 30))



    # 🔹 Footer
    footer_data = [
        [
            Paragraph("Người xét duyệt", styles["NormalVN"]),
            Paragraph("Người lập báo cáo", styles["RightBold"])
        ]
    ]
    footer_table = Table(footer_data, colWidths=[8 * cm, 8 * cm])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,-1), 'DejaVu'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('TOPPADDING', (0,0), (-1,-1), 30),
    ]))
    story.append(footer_table)

    doc.build(story)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="bao_cao_hoa_hong.pdf",
        mimetype="application/pdf"
    )




if __name__ == '__main__':
    app.run(debug=True)