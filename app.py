from flask import Flask, render_template, request

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

if __name__ == '__main__':
    app.run(debug=True)