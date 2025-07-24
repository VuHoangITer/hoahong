from flask import Flask, render_template, request

app = Flask(__name__)


def get_price(product, quantity):
    if product == "KDG XÁM PHỔ THÔNG":
        if quantity >= 100:
            return 125000
        elif quantity >= 50:
            return 140000
        elif quantity >= 20:
            return 145000
        elif quantity >= 10:
            return 150000
    elif product == "KDG TRẮNG PHỔ THÔNG":
        if quantity >= 100:
            return 140000
        elif quantity >= 50:
            return 155000
        elif quantity >= 20:
            return 160000
        elif quantity >= 10:
            return 165000
    return 0


def get_market_price(product):
    return 195000 if product == "KDG XÁM PHỔ THÔNG" else 250000


@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    after_gift_price = None
    approved = None

    if request.method == 'POST':
        product = request.form['product']
        sell_qty = int(request.form['sell_qty'])
        # 👉 Kiểm tra số lượng bán phải >= 10
        if sell_qty < 10:
            return render_template('index.html', result={
                'error': 'Số lượng bán phải từ 10 trở lên.'
            })
        gift_qty = int(request.form['gift_qty'])
        total_qty = sell_qty + gift_qty
        G = get_price(product, sell_qty)
        D = get_market_price(product)

        if total_qty > 0:
            after_gift_price = (D * sell_qty) / total_qty
            approved = after_gift_price > G

            result = {
                'product': product,
                'sell_qty': sell_qty,
                'gift_qty': gift_qty,
                'G': G,
                'D': D,
                'after_gift_price': after_gift_price,
                'approved': approved
            }

            # Nếu được duyệt và đã nhập giá trị quà tặng
            if approved and 'gift_value' in request.form:
                gift_value = int(request.form['gift_value'])
                fund = (after_gift_price - G) * total_qty
                base_commission = 8000 if product == "KDG XÁM PHỔ THÔNG" else 0
                company_commission = base_commission * sell_qty
                bonus = fund - gift_value
                total_commission = bonus + company_commission

                result['commission_data'] = {
                    'fund': fund,
                    'gift_value': gift_value,
                    'bonus': bonus,
                    'total_commission': total_commission
                }

    return render_template('index.html', result=result)


if __name__ == '__main__':
    app.run(debug=True)
