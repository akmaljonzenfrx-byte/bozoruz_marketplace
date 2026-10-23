import os
import random
from functools import wraps
from flask import (
    Flask, render_template, request, jsonify, session,
    redirect, url_for, flash, abort, g
)

from database import (
    init_db, seed_initial_data, get_db,
    hash_password, check_password, get_products,
    get_product_by_id, create_order, get_user_by_phone,
    apply_promo_code
)
from admin import admin_bp

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bozoruz-ultra-secure-secret-key-2025-marketplace')
app.config['JSON_AS_ASCII'] = False

# Blueprint ro'yxatdan o'tkazish
app.register_blueprint(admin_bp, url_prefix='/admin')


@app.before_request
def setup_request_state():
    """Har bir so'rovdan oldin baza ulanishi va sessiya sozlamalari"""
    g.db = get_db()
    if 'cart' not in session:
        session['cart'] = {}  # {product_id_str: {"quantity": int, "variant": str}}
    if 'wishlist' not in session:
        session['wishlist'] = []  # [product_id_int, ...]
    if 'compare' not in session:
        session['compare'] = []  # [product_id_int, ...]
    if 'recently_viewed' not in session:
        session['recently_viewed'] = []  # [product_id_int, ...]

    user_id = session.get('user_id')
    g.user = None
    if user_id:
        cursor = g.db.cursor()
        cursor.execute("SELECT id, name, phone, email, role, avatar_color FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            g.user = dict(row)


@app.teardown_appcontext
def close_db_connection(exception=None):
    """Sessiya tugaganda DB ulanishni xavfsiz yopish"""
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@app.context_processor
def inject_global_data():
    """Barcha Jinja2 shablonlariga umumiy o'zgaruvchilarni uzatish"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name, slug, icon, bg_color FROM categories WHERE parent_id IS NULL ORDER BY sort_order ASC")
    categories = [dict(row) for row in cursor.fetchall()]

    cart_total_qty = sum(item.get('quantity', 1) for item in session.get('cart', {}).values())
    wishlist_count = len(session.get('wishlist', []))
    compare_count = len(session.get('compare', []))

    return {
        'nav_categories': categories,
        'cart_count': cart_total_qty,
        'wishlist_count': wishlist_count,
        'compare_count': compare_count,
        'current_user': g.user,
    }


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user:
            flash("Iltimos, avval tizimga kiring!", "warning")
            return redirect(url_for('auth_login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# ASOSIY SAHIFALAR VA KATALOG
# ==========================================

@app.route('/')
def index():
    """Asosiy bosh sahifa: bannerlar, chegirmalar, yangi va tavsiya etilgan tovarlar"""
    db = get_db()
    cursor = db.cursor()

    # Faol bannerlar
    cursor.execute("SELECT * FROM banners WHERE is_active = 1 ORDER BY sort_order ASC")
    banners = [dict(row) for row in cursor.fetchall()]

    # Aksiya mahsulotlari (chegirmasi eng yuqori bo'lganlar)
    flash_sale_products = get_products({'is_sale': True, 'limit': 6})

    # Ommabop tovarlar (yuqori reyting va ko'p buyurtma)
    popular_products = get_products({'sort': 'popular', 'limit': 8})

    # Yangi kelgan tovarlar
    new_products = get_products({'sort': 'newest', 'limit': 8})

    # Tavsiya etilgan tovarlar
    recommended_products = get_products({'sort': 'rating', 'limit': 8})

    # Yaqinda ko'rilgan tovarlar
    recently_viewed_products = []
    if session.get('recently_viewed'):
        r_ids = session['recently_viewed'][:6]
        placeholders = ','.join(['?'] * len(r_ids))
        cursor.execute(f"SELECT * FROM products WHERE id IN ({placeholders}) AND is_active = 1", r_ids)
        r_dict = {row['id']: dict(row) for row in cursor.fetchall()}
        recently_viewed_products = [r_dict[pid] for pid in r_ids if pid in r_dict]

    return render_template(
        'index.html',
        banners=banners,
        flash_sale_products=flash_sale_products,
        popular_products=popular_products,
        new_products=new_products,
        recommended_products=recommended_products,
        recently_viewed=recently_viewed_products
    )


@app.route('/katalog')
def catalog():
    """Katalog va qidiruv natijalari filtrlash, saralash va sahifalash bilan"""
    category_slug = request.args.get('kategoriya')
    search_query = request.args.get('q', '').strip()
    min_price = request.args.get('min_narx', type=int)
    max_price = request.args.get('max_narx', type=int)
    has_discount = request.args.get('chegirma') == '1'
    sort_by = request.args.get('saralash', 'popular')
    page = request.args.get('sahifa', 1, type=int)
    per_page = 16

    db = get_db()
    cursor = db.cursor()

    active_category = None
    category_id = None
    if category_slug:
        cursor.execute("SELECT * FROM categories WHERE slug = ?", (category_slug,))
        row = cursor.fetchone()
        if row:
            active_category = dict(row)
            category_id = active_category['id']

    filters = {
        'category_id': category_id,
        'search': search_query,
        'min_price': min_price,
        'max_price': max_price,
        'has_discount': has_discount,
        'sort': sort_by,
        'page': page,
        'per_page': per_page
    }

    products_data = get_products(filters)
    total_count = products_data.get('total_count', 0) if isinstance(products_data, dict) else len(products_data)
    items = products_data.get('items', products_data) if isinstance(products_data, dict) else products_data

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    # Barcha brendlar va kategoriyalar ro'yxati filtrlash uchun
    cursor.execute("SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL AND brand != '' ORDER BY brand ASC")
    brands = [row['brand'] for row in cursor.fetchall()]

    return render_template(
        'catalog.html',
        products=items,
        total_count=total_count,
        current_page=page,
        total_pages=total_pages,
        active_category=active_category,
        search_query=search_query,
        min_price=min_price,
        max_price=max_price,
        has_discount=has_discount,
        sort_by=sort_by,
        brands=brands
    )


@app.route('/mahsulot/<int:product_id>')
def product_detail(product_id: int):
    """Mahsulot sahifasi, tavsif, sharhlar va muddatli to'lov kalkulyatori"""
    product = get_product_by_id(product_id)
    if not product:
        abort(404)

    # Yaqinda ko'rilganlarga qo'shish
    rv = session.get('recently_viewed', [])
    if product_id in rv:
        rv.remove(product_id)
    rv.insert(0, product_id)
    session['recently_viewed'] = rv[:10]
    session.modified = True

    # O'xshash tovarlar
    similar_products = get_products({
        'category_id': product.get('category_id'),
        'limit': 5,
        'exclude_id': product_id
    })

    # Foydalanuvchi ushbu tovar uchun narx tushish obunasini olganmi?
    has_price_alert = False
    if g.user:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id FROM price_alerts WHERE user_id = ? AND product_id = ?", (g.user['id'], product_id))
        if cur.fetchone():
            has_price_alert = True

    return render_template(
        'product.html',
        product=product,
        similar_products=similar_products,
        has_price_alert=has_price_alert
    )


@app.route('/api/qidiruv/tavsiyalar')
def api_search_suggestions():
    """Qidiruv panelida yozganda jonli avto-tavsiyalar (Live Search)"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'results': []})

    db = get_db()
    cursor = db.cursor()
    search_param = f"%{query}%"

    cursor.execute("""
        SELECT id, name, price, discount_percent, image_icon, bg_gradient 
        FROM products 
        WHERE is_active = 1 AND (name LIKE ? OR brand LIKE ? OR category_name LIKE ?)
        LIMIT 6
    """, (search_param, search_param, search_param))

    rows = cursor.fetchall()
    results = []
    for r in rows:
        price = r['price']
        discount = r['discount_percent']
        current_price = int(price * (100 - discount) / 100) if discount > 0 else price
        results.append({
            'id': r['id'],
            'name': r['name'],
            'price': current_price,
            'formatted_price': f"{current_price:,}".replace(',', ' ') + " so'm",
            'icon': r['image_icon'],
            'bg': r['bg_gradient'],
            'url': url_for('product_detail', product_id=r['id'])
        })

    return jsonify({'results': results})


# ==========================================
# SAVAT VA SEVIMLILAR (AJAX & VIEW)
# ==========================================

@app.route('/savat')
def cart_view():
    """Savat ko'rinishi va hisob-kitoblar"""
    cart = session.get('cart', {})
    cart_items = []
    total_original = 0
    total_discount = 0

    if cart:
        db = get_db()
        cursor = db.cursor()
        product_ids = [int(pid) for pid in cart.keys()]
        placeholders = ','.join(['?'] * len(product_ids))
        cursor.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", product_ids)
        products_map = {p['id']: dict(p) for p in cursor.fetchall()}

        for pid_str, item_info in cart.items():
            pid = int(pid_str)
            product = products_map.get(pid)
            if not product:
                continue

            quantity = item_info.get('quantity', 1)
            variant = item_info.get('variant', 'Asosiy')
            base_price = product['price']
            discount_pct = product['discount_percent'] or 0
            final_price = int(base_price * (100 - discount_pct) / 100)

            item_original_sum = base_price * quantity
            item_final_sum = final_price * quantity

            total_original += item_original_sum
            total_discount += (item_original_sum - item_final_sum)

            cart_items.append({
                'product': product,
                'variant': variant,
                'quantity': quantity,
                'unit_price': final_price,
                'original_price': base_price,
                'total_price': item_final_sum,
                'stock': product['stock']
            })

    total_final = total_original - total_discount

    return render_template(
        'cart.html',
        cart_items=cart_items,
        total_original=total_original,
        total_discount=total_discount,
        total_final=total_final
    )


@app.route('/api/savat/qoshish', methods=['POST'])
def add_to_cart_api():
    """Savatga tovar qo'shish API"""
    data = request.get_json() or {}
    product_id = str(data.get('product_id'))
    quantity = int(data.get('quantity', 1))
    variant = data.get('variant', 'Standart')

    if not product_id:
        return jsonify({'success': False, 'message': 'Mahsulot ID topilmadi'}), 400

    product = get_product_by_id(int(product_id))
    if not product:
        return jsonify({'success': False, 'message': 'Mahsulot mavjud emas'}), 404

    cart = session.get('cart', {})
    if product_id in cart:
        new_qty = cart[product_id]['quantity'] + quantity
        if new_qty > product['stock']:
            new_qty = product['stock']
        cart[product_id]['quantity'] = new_qty
        cart[product_id]['variant'] = variant
    else:
        cart[product_id] = {
            'quantity': min(quantity, product['stock']),
            'variant': variant
        }

    session['cart'] = cart
    session.modified = True

    total_count = sum(item['quantity'] for item in cart.values())
    return jsonify({
        'success': True,
        'message': f"'{product['name']}' savatga muvaffaqiyatli qo'shildi!",
        'cart_count': total_count
    })


@app.route('/api/savat/yangilash', methods=['POST'])
def update_cart_api():
    """Savatdagi mahsulot miqdorini o'zgartirish yoki o'chirish"""
    data = request.get_json() or {}
    product_id = str(data.get('product_id'))
    action = data.get('action')  # 'increase', 'decrease', 'set', 'remove'
    new_quantity = data.get('quantity')

    cart = session.get('cart', {})
    if product_id not in cart:
        return jsonify({'success': False, 'message': 'Tovarga oid maʼlumot topilmadi'}), 404

    product = get_product_by_id(int(product_id))
    stock = product['stock'] if product else 999

    if action == 'remove':
        cart.pop(product_id, None)
    elif action == 'increase':
        if cart[product_id]['quantity'] < stock:
            cart[product_id]['quantity'] += 1
    elif action == 'decrease':
        if cart[product_id]['quantity'] > 1:
            cart[product_id]['quantity'] -= 1
        else:
            cart.pop(product_id, None)
    elif action == 'set' and new_quantity is not None:
        q = int(new_quantity)
        if q <= 0:
            cart.pop(product_id, None)
        else:
            cart[product_id]['quantity'] = min(q, stock)

    session['cart'] = cart
    session.modified = True

    total_count = sum(item['quantity'] for item in cart.values())
    return jsonify({
        'success': True,
        'cart_count': total_count
    })


@app.route('/api/sevimlilar/almashtirish', methods=['POST'])
def toggle_wishlist_api():
    """Sevimlilarga qo'shish yoki olib tashlash"""
    data = request.get_json() or {}
    product_id = int(data.get('product_id', 0))

    wishlist = session.get('wishlist', [])
    if product_id in wishlist:
        wishlist.remove(product_id)
        is_favorite = False
        msg = "Mahsulot sevimlilardan olib tashlandi"
    else:
        wishlist.append(product_id)
        is_favorite = True
        msg = "Mahsulot sevimlilarga saqlandi!"

    session['wishlist'] = wishlist
    session.modified = True

    return jsonify({
        'success': True,
        'is_favorite': is_favorite,
        'message': msg,
        'count': len(wishlist)
    })


@app.route('/sevimlilar')
def wishlist_view():
    """Sevimlilar ro'yxati sahifasi"""
    wishlist_ids = session.get('wishlist', [])
    products = []
    if wishlist_ids:
        db = get_db()
        cursor = db.cursor()
        placeholders = ','.join(['?'] * len(wishlist_ids))
        cursor.execute(f"SELECT * FROM products WHERE id IN ({placeholders}) AND is_active = 1", wishlist_ids)
        products = [dict(row) for row in cursor.fetchall()]

    return render_template('wishlist.html', products=products)


# ==========================================
# BUYURTMA VA TO'LOV TIZIMI (CHECKOUT)
# ==========================================

@app.route('/buyurtma-berish', methods=['GET', 'POST'])
def checkout():
    """Buyurtmani rasmiylashtirish sahifasi va amali"""
    cart = session.get('cart', {})
    if not cart:
        flash("Savatingiz bo'sh. Iltimos, xarid qilish uchun tovar tanlang.", "info")
        return redirect(url_for('catalog'))

    db = get_db()
    cursor = db.cursor()

    product_ids = [int(pid) for pid in cart.keys()]
    placeholders = ','.join(['?'] * len(product_ids))
    cursor.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", product_ids)
    products_map = {p['id']: dict(p) for p in cursor.fetchall()}

    items_to_order = []
    subtotal = 0
    for pid_str, item_info in cart.items():
        pid = int(pid_str)
        product = products_map.get(pid)
        if not product:
            continue
        qty = item_info.get('quantity', 1)
        discount_pct = product['discount_percent'] or 0
        final_price = int(product['price'] * (100 - discount_pct) / 100)
        items_to_order.append({
            'product_id': pid,
            'product_name': product['name'],
            'quantity': qty,
            'unit_price': final_price,
            'total_price': final_price * qty,
            'variant': item_info.get('variant', 'Standart')
        })
        subtotal += final_price * qty

    delivery_fee = 0 if subtotal >= 200000 else 20000
    grand_total = subtotal + delivery_fee

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', 'Toshkent shahri')
        address = request.form.get('address', '').strip()
        delivery_method = request.form.get('delivery_method', 'kuryer')
        payment_method = request.form.get('payment_method', 'naqd')
        installment_months = request.form.get('installment_months', type=int)
        promo_code = request.form.get('promo_code', '').strip().upper()
        comment = request.form.get('comment', '').strip()

        if not full_name or not phone or not address:
            flash("Iltimos, barcha majburiy maydonlarni to'ldiring!", "danger")
            return render_template('checkout.html', items=items_to_order, subtotal=subtotal, delivery_fee=delivery_fee, grand_total=grand_total)

        # Promokod tekshiruvi
        promo_discount = 0
        if promo_code:
            promo_res = apply_promo_code(promo_code, subtotal)
            if promo_res.get('valid'):
                promo_discount = promo_res.get('discount_amount', 0)
                grand_total = max(0, grand_total - promo_discount)

        shipping_data = {
            'full_name': full_name,
            'phone': phone,
            'city': city,
            'address': address,
            'delivery_method': delivery_method,
            'payment_method': payment_method,
            'installment_months': installment_months if payment_method == 'muddatli' else None,
            'delivery_fee': delivery_fee,
            'promo_discount': promo_discount,
            'subtotal': subtotal,
            'grand_total': grand_total,
            'comment': comment
        }

        user_id = g.user['id'] if g.user else None
        order_info = create_order(user_id=user_id, items=items_to_order, shipping_data=shipping_data, promo_code=promo_code)

        # Savatni tozalash
        session['cart'] = {}
        session.modified = True

        return redirect(url_for('order_success', order_number=order_info['order_number']))

    return render_template(
        'checkout.html',
        items=items_to_order,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        grand_total=grand_total
    )


@app.route('/buyurtma-tasdiqlandi/<order_number>')
def order_success(order_number: str):
    """Buyurtma muvaffaqiyatli rasmiylashtirilganligi haqidagi sahifa"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,))
    order = cursor.fetchone()
    if not order:
        abort(404)

    return render_template('order_success.html', order=dict(order))


@app.route('/hisob-faktura/<order_number>')
def order_invoice(order_number: str):
    """Chop etiladigan rasmiy hisob-faktura sahifasi (Print invoice)"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,))
    order_row = cursor.fetchone()
    if not order_row:
        abort(404)

    order = dict(order_row)
    cursor.execute("""
        SELECT oi.*, p.name as product_name, p.brand, p.image_icon 
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    """, (order['id'],))
    items = [dict(row) for row in cursor.fetchall()]

    return render_template('invoice.html', order=order, items=items)


@app.route('/api/promokod/tekshirish', methods=['POST'])
def api_check_promo():
    """Promokodni tekshirish va chegirma hisoblash API"""
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    total_sum = int(data.get('total_sum', 0))

    if not code:
        return jsonify({'success': False, 'message': 'Promokod kiritilmadi'})

    result = apply_promo_code(code, total_sum)
    return jsonify(result)


# ==========================================
# FOYDALANUVCHI AVTORIZATSIYA (SMS SIMULATSIYA)
# ==========================================

@app.route('/kirish', methods=['GET', 'POST'])
def auth_login():
    """Telefon raqam orqali tezkor kirish yoki SMS orqali tasdiqlash"""
    if g.user:
        return redirect(url_for('index'))

    next_url = request.args.get('next') or request.form.get('next') or url_for('index')

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip().replace(' ', '').replace('-', '')
        password = request.form.get('password', '')

        user = get_user_by_phone(phone)
        if user and check_password(password, user['password_hash']):
            session['user_id'] = user['id']
            session['user_phone'] = user['phone']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            flash(f"Xush kelibsiz, {user['name']}!", "success")
            return redirect(next_url)
        else:
            flash("Telefon raqami yoki parol noto'g'ri!", "danger")

    return render_template('auth_login.html', next=next_url)


@app.route('/api/auth/sms-yuborish', methods=['POST'])
def auth_send_sms():
    """SMS simulyatsiyasi: kod yaratish va ekranga chiqarish uchun qaytarish"""
    data = request.get_json() or {}
    phone = data.get('phone', '').strip().replace(' ', '').replace('-', '')

    if not phone or len(phone) < 9:
        return jsonify({'success': False, 'message': "Iltimos, to'liq telefon raqam kiriting (+998XXXXXXXXX)"}), 400

    simulated_sms_code = str(random.randint(100000, 999999))
    session['sms_verification'] = {
        'phone': phone,
        'code': simulated_sms_code
    }
    session.modified = True

    return jsonify({
        'success': True,
        'message': "SMS tasdiqlash kodi muvaffaqiyatli yuborildi!",
        'simulated_code': simulated_sms_code  # O'quv maqsadida ekranda ko'rsatiladi
    })


@app.route('/api/auth/sms-tasdiqlash', methods=['POST'])
def auth_verify_sms():
    """Kiritilgan SMS kodni tasdiqlash va tizimga kiritish"""
    data = request.get_json() or {}
    code = data.get('code', '').strip()
    name = data.get('name', 'BozorUz Xaridori').strip()
    password = data.get('password', '')

    saved_sms = session.get('sms_verification')
    if not saved_sms or saved_sms.get('code') != code:
        return jsonify({'success': False, 'message': "SMS tasdiqlash kodi noto'g'ri yoki eskirgan!"}), 400

    phone = saved_sms.get('phone')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()

    if not user:
        # Yangi foydalanuvchi yaratish
        pass_to_hash = password if password else "BozorUz123"
        hashed = hash_password(pass_to_hash)
        colors = ['#6366F1', '#10B981', '#EC4899', '#F59E0B', '#8B5CF6']
        avatar_color = random.choice(colors)

        cursor.execute("""
            INSERT INTO users (phone, name, password_hash, role, avatar_color, created_at)
            VALUES (?, ?, ?, 'customer', ?, datetime('now'))
        """, (phone, name, hashed, avatar_color))
        db.commit()
        user_id = cursor.lastrowid
    else:
        user_id = user['id']
        name = user['name']

    # Sessiyaga yozish
    session.pop('sms_verification', None)
    session['user_id'] = user_id
    session['user_phone'] = phone
    session['user_name'] = name
    session['user_role'] = 'customer'
    session.modified = True

    return jsonify({
        'success': True,
        'message': "Avtorizatsiya muvaffaqiyatli amalga oshirildi!",
        'user_name': name
    })


@app.route('/chiqish')
def auth_logout():
    """Foydalanuvchi sessiyasini yakunlash"""
    session.pop('user_id', None)
    session.pop('user_phone', None)
    session.pop('user_name', None)
    session.pop('user_role', None)
    flash("Siz profilingizdan chiqdingiz.", "info")
    return redirect(url_for('index'))


@app.route('/profil')
@login_required
def profile_view():
    """Foydalanuvchi shaxsiy kabineti, buyurtmalar tarixi va manzillari"""
    db = get_db()
    cursor = db.cursor()

    # Buyurtmalar tarixi
    cursor.execute("""
        SELECT * FROM orders 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    """, (g.user['id'],))
    orders = [dict(row) for row in cursor.fetchall()]

    for o in orders:
        cursor.execute("""
            SELECT oi.*, p.name as product_name, p.image_icon 
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (o['id'],))
        o['items'] = [dict(it) for it in cursor.fetchall()]

    # Saqlangan narx o'zgarishi bildirishnomalari
    cursor.execute("""
        SELECT pa.*, p.name, p.price, p.image_icon, p.bg_gradient 
        FROM price_alerts pa
        JOIN products p ON pa.product_id = p.id
        WHERE pa.user_id = ?
        ORDER BY pa.created_at DESC
    """, (g.user['id'],))
    price_alerts = [dict(row) for row in cursor.fetchall()]

    return render_template('profile.html', user=g.user, orders=orders, price_alerts=price_alerts)


# ==========================================
# QO'SHIMCHA AQLLI FUNKSIYALAR
# ==========================================

@app.route('/solishtirish')
def compare_view():
    """Mahsulotlarni solishtirish sahifasi"""
    compare_ids = session.get('compare', [])
    products = []
    if compare_ids:
        db = get_db()
        cursor = db.cursor()
        placeholders = ','.join(['?'] * len(compare_ids))
        cursor.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", compare_ids)
        products = [dict(row) for row in cursor.fetchall()]

    return render_template('compare.html', products=products)


@app.route('/api/solishtirish/almashtirish', methods=['POST'])
def toggle_compare_api():
    """Mahsulotni taqqoslash ro'yxatiga qo'shish yoki undan olish"""
    data = request.get_json() or {}
    product_id = int(data.get('product_id', 0))

    compare = session.get('compare', [])
    if product_id in compare:
        compare.remove(product_id)
        is_in = False
        msg = "Mahsulot taqqoslash ro'yxatidan olib tashlandi"
    else:
        if len(compare) >= 4:
            return jsonify({'success': False, 'message': "Bir vaqtning o'zida ko'pi bilan 4 ta mahsulotni solishtirish mumkin!"}), 400
        compare.append(product_id)
        is_in = True
        msg = "Mahsulot taqqoslashga qo'shildi!"

    session['compare'] = compare
    session.modified = True

    return jsonify({
        'success': True,
        'is_in_compare': is_in,
        'message': msg,
        'count': len(compare)
    })


@app.route('/api/narx-tushsa-xabar-ber', methods=['POST'])
def add_price_alert_api():
    """'Narx tushsa xabar ber' funksiyasiga obuna bo'lish"""
    data = request.get_json() or {}
    product_id = int(data.get('product_id', 0))
    target_price = data.get('target_price', type=int)

    if not product_id:
        return jsonify({'success': False, 'message': 'Mahsulot ko‘rsatilmadi'}), 400

    if not g.user:
        return jsonify({'success': False, 'message': 'Ushbu amal uchun tizimga kiring', 'need_login': True}), 401

    db = get_db()
    cursor = db.cursor()

    # Avval mavjudligini tekshirish
    cursor.execute("SELECT id FROM price_alerts WHERE user_id = ? AND product_id = ?", (g.user['id'], product_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM price_alerts WHERE id = ?", (existing['id'],))
        db.commit()
        return jsonify({'success': True, 'subscribed': False, 'message': "Xabarnoma bekor qilindi."})
    else:
        cursor.execute("""
            INSERT INTO price_alerts (user_id, product_id, target_price, created_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (g.user['id'], product_id, target_price))
        db.commit()
        return jsonify({'success': True, 'subscribed': True, 'message': "Narx arzonlashganda sizga darhol xabar qilamiz!"})


@app.route('/api/sharh-qoshish', methods=['POST'])
@login_required
def add_review_api():
    """Mahsulotga xaridor sharhi va yulduzli reyting qo'shish"""
    data = request.get_json() or {}
    product_id = int(data.get('product_id', 0))
    rating = int(data.get('rating', 5))
    comment = data.get('comment', '').strip()

    if not product_id or not comment:
        return jsonify({'success': False, 'message': "Iltimos, sharh matnini to'liq yozing!"}), 400

    rating = max(1, min(5, rating))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO reviews (product_id, user_id, user_name, rating, comment, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (product_id, g.user['id'], g.user['name'], rating, comment))

    # Mahsulotning umumiy reytingini qayta hisoblash
    cursor.execute("SELECT AVG(rating) as avg_r, COUNT(id) as count_r FROM reviews WHERE product_id = ?", (product_id,))
    stats = cursor.fetchone()
    if stats and stats['count_r'] > 0:
        new_rating = round(stats['avg_r'], 1)
        cursor.execute("UPDATE products SET rating = ?, reviews_count = ? WHERE id = ?", (new_rating, stats['count_r'], product_id))

    db.commit()

    return jsonify({
        'success': True,
        'message': "Sharhingiz qabul qilindi, fikringiz uchun rahmat!",
        'user_name': g.user['name'],
        'rating': rating,
        'comment': comment
    })


# ==========================================
# XATOLIKLARNI QAYTA ISHLASH (ERROR HANDLERS)
# ==========================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500


# ==========================================
# DASTURNI ISHGA TUSHIRISH
# ==========================================

# Ilova yuklanganda bazani initsializatsiya qilish va to'ldirish
with app.app_context():
    init_db()
    seed_initial_data()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"==================================================")
    print(f"🚀 BozorUz platformasi ishga tushmoqda!")
    print(f"🌐 Manzil: http://localhost:{port}")
    print(f"👤 Admin panel: http://localhost:{port}/admin/kirish")
    print(f"🔑 Admin login: admin / admin123")
    print(f"==================================================")
    app.run(host='0.0.0.0', port=port, debug=True)