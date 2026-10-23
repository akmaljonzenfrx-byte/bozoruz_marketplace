import functools
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import (
    get_db,
    check_password,
    hash_password,
    get_dashboard_analytics,
    get_product_by_id
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(view_func):
    """Admin yoki sotuvchi avtorizatsiyasini tekshiruvchi dekorator."""
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if 'admin_user_id' not in session:
            flash("Boshqaruv paneliga kirish uchun tizimga kiring.", "warning")
            return redirect(url_for('admin.admin_login'))
        return view_func(*args, **kwargs)
    return wrapped_view

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """Admin va sotuvchilar uchun kirish sahifasi."""
    if 'admin_user_id' in session:
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '').strip()

        if not login or not password:
            flash("Iltimos, barcha maydonlarni to'ldiring.", "danger")
            return render_template('admin/login.html')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE (phone = ? OR phone = ? OR id IN (SELECT id FROM users WHERE full_name = ?)) AND role IN ('admin', 'seller')",
            (login, login.replace('+', '').replace(' ', ''), login)
        )
        user = cursor.fetchone()

        # Agar maxsus 'admin' logini kiritilgan bo'lsa
        if not user and login == 'admin':
            cursor.execute("SELECT * FROM users WHERE role = 'admin' LIMIT 1")
            user = cursor.fetchone()

        if user and check_password(password, user['password_hash']):
            session['admin_user_id'] = user['id']
            session['admin_user_name'] = user['full_name']
            session['admin_user_role'] = user['role']
            session['admin_seller_id'] = user['seller_id']

            # Standart parolni o'zgartirish eslatmasi
            if password == 'admin123':
                flash("XAVFSIZLIK ESLATMASI: Siz standart 'admin123' parolidan foydalanmoqdasiz. Iltimos, xavfsizlik uchun parolingizni o'zgartiring!", "warning")
            else:
                flash(f"Xush kelibsiz, {user['full_name']}!", "success")

            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash("Login yoki parol noto'g'ri, yoxud sizda ma'muriy huquqlar mavjud emas.", "danger")

    return render_template('admin/login.html')

@admin_bp.route('/logout')
def admin_logout():
    """Boshqaruv panelidan chiqish."""
    session.pop('admin_user_id', None)
    session.pop('admin_user_name', None)
    session.pop('admin_user_role', None)
    session.pop('admin_seller_id', None)
    flash("Boshqaruv panelidan muvaffaqiyatli chiqdingiz.", "info")
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    """Asosiy analitika va statistika paneli."""
    analytics = get_dashboard_analytics()
    conn = get_db()
    cursor = conn.cursor()

    # So'nggi 5 ta buyurtma
    cursor.execute("""
        SELECT o.*, u.full_name as user_name, u.phone as user_phone
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
        LIMIT 5
    """)
    recent_orders = [dict(row) for row in cursor.fetchall()]

    # Kam qolgan tovarlar (zaxirasi <= 5)
    cursor.execute("""
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.stock <= 5 AND p.is_active = 1
        ORDER BY p.stock ASC
        LIMIT 6
    """)
    low_stock_products = [dict(row) for row in cursor.fetchall()]

    # Sotuvchilar soni
    cursor.execute("SELECT COUNT(*) as cnt FROM sellers")
    sellers_count = cursor.fetchone()['cnt']

    return render_template(
        'admin/dashboard.html',
        analytics=analytics,
        recent_orders=recent_orders,
        low_stock_products=low_stock_products,
        sellers_count=sellers_count
    )

@admin_bp.route('/products')
@admin_required
def admin_products():
    """Mahsulotlar ro'yxati, filtrlash va zaxira nazorati."""
    search = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    stock_status = request.args.get('stock_status', '')

    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT p.*, c.name as category_name, s.shop_name as seller_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN sellers s ON p.seller_id = s.id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (p.name LIKE ? OR p.brand LIKE ? OR p.sku LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)

    if stock_status == 'low':
        query += " AND p.stock <= 5"
    elif stock_status == 'out':
        query += " AND p.stock = 0"

    query += " ORDER BY p.id DESC"

    cursor.execute(query, params)
    products = [dict(row) for row in cursor.fetchall()]

    # Kategoriyalar ro'yxati (filtr uchun)
    cursor.execute("SELECT id, name FROM categories ORDER BY name ASC")
    categories = [dict(row) for row in cursor.fetchall()]

    return render_template(
        'admin/products.html',
        products=products,
        categories=categories,
        current_search=search,
        current_category=category_id,
        current_stock=stock_status
    )

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    """Yangi mahsulot qo'shish."""
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', type=int)
        seller_id = request.form.get('seller_id', type=int) or 1
        price = request.form.get('price', type=int) or 0
        old_price = request.form.get('old_price', type=int) or None
        stock = request.form.get('stock', type=int) or 0
        brand = request.form.get('brand', '').strip()
        icon = request.form.get('icon', '📦').strip()
        color_theme = request.form.get('color_theme', 'from-blue-600 to-indigo-700').strip()
        short_desc = request.form.get('short_description', '').strip()
        description = request.form.get('description', '').strip()
        variants_json = request.form.get('variants_json', '[]').strip()
        specs_json = request.form.get('specs_json', '{}').strip()
        is_flash_sale = 1 if request.form.get('is_flash_sale') == 'on' else 0
        is_featured = 1 if request.form.get('is_featured') == 'on' else 0

        # SKU avtomatik generatsiya qilish
        sku = request.form.get('sku', '').strip()
        if not sku:
            import random
            sku = f"BZ-{random.randint(10000, 99999)}"

        if not name or not category_id or price <= 0:
            flash("Mahsulot nomi, toifasi va narxini to'g'ri kiriting.", "danger")
        else:
            try:
                cursor.execute("""
                    INSERT INTO products (
                        name, category_id, seller_id, sku, price, old_price, stock,
                        brand, icon, color_theme, short_description, description,
                        variants_json, specs_json, is_flash_sale, is_featured, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    name, category_id, seller_id, sku, price, old_price, stock,
                    brand, icon, color_theme, short_desc, description,
                    variants_json, specs_json, is_flash_sale, is_featured
                ))
                conn.commit()
                flash(f"'{name}' mahsuloti muvaffaqiyatli qo'shildi!", "success")
                return redirect(url_for('admin.admin_products'))
            except Exception as e:
                conn.rollback()
                flash(f"Xatolik yuz berdi: {str(e)}", "danger")

    cursor.execute("SELECT id, name FROM categories ORDER BY name ASC")
    categories = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT id, shop_name FROM sellers ORDER BY shop_name ASC")
    sellers = [dict(row) for row in cursor.fetchall()]

    return render_template('admin/product_form.html', product=None, categories=categories, sellers=sellers)

@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id: int):
    """Mavjud mahsulotni tahrirlash."""
    product = get_product_by_id(product_id)
    if not product:
        flash("Bunday mahsulot topilmadi.", "danger")
        return redirect(url_for('admin.admin_products'))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', type=int)
        seller_id = request.form.get('seller_id', type=int) or product['seller_id']
        price = request.form.get('price', type=int) or 0
        old_price = request.form.get('old_price', type=int) or None
        stock = request.form.get('stock', type=int) or 0
        brand = request.form.get('brand', '').strip()
        icon = request.form.get('icon', product['icon']).strip()
        color_theme = request.form.get('color_theme', product['color_theme']).strip()
        short_desc = request.form.get('short_description', '').strip()
        description = request.form.get('description', '').strip()
        variants_json = request.form.get('variants_json', '[]').strip()
        specs_json = request.form.get('specs_json', '{}').strip()
        is_flash_sale = 1 if request.form.get('is_flash_sale') == 'on' else 0
        is_featured = 1 if request.form.get('is_featured') == 'on' else 0
        is_active = 1 if request.form.get('is_active') == 'on' else 0
        sku = request.form.get('sku', product['sku']).strip()

        if not name or not category_id or price <= 0:
            flash("Mahsulot nomi, toifasi va narxini to'g'ri kiriting.", "danger")
        else:
            try:
                cursor.execute("""
                    UPDATE products SET
                        name = ?, category_id = ?, seller_id = ?, sku = ?, price = ?,
                        old_price = ?, stock = ?, brand = ?, icon = ?, color_theme = ?,
                        short_description = ?, description = ?, variants_json = ?,
                        specs_json = ?, is_flash_sale = ?, is_featured = ?, is_active = ?
                    WHERE id = ?
                """, (
                    name, category_id, seller_id, sku, price, old_price, stock,
                    brand, icon, color_theme, short_desc, description,
                    variants_json, specs_json, is_flash_sale, is_featured, is_active,
                    product_id
                ))
                conn.commit()
                flash(f"'{name}' ma'lumotlari muvaffaqiyatli yangilandi!", "success")
                return redirect(url_for('admin.admin_products'))
            except Exception as e:
                conn.rollback()
                flash(f"Xatolik yuz berdi: {str(e)}", "danger")

    cursor.execute("SELECT id, name FROM categories ORDER BY name ASC")
    categories = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT id, shop_name FROM sellers ORDER BY shop_name ASC")
    sellers = [dict(row) for row in cursor.fetchall()]

    return render_template('admin/product_form.html', product=product, categories=categories, sellers=sellers)

@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id: int):
    """Mahsulotni o'chirish yoki nofaol qilish."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Mahsulot buyurtmalarda mavjudligini tekshirish
        cursor.execute("SELECT COUNT(*) as cnt FROM order_items WHERE product_id = ?", (product_id,))
        count = cursor.fetchone()['cnt']
        if count > 0:
            # Agar buyurtmalarda bo'lsa, xatolik chiqarmaslik uchun shunchaki is_active = 0 qilinadi
            cursor.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
            flash("Mahsulot avvalgi buyurtmalarda mavjud bo'lgani sababli arxivlandi (nofaol qilindi).", "info")
        else:
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            flash("Mahsulot butunlay o'chirildi.", "success")
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"O'chirishda xatolik yuz berdi: {str(e)}", "danger")

    return redirect(url_for('admin.admin_products'))

@admin_bp.route('/orders')
@admin_required
def admin_orders():
    """Barcha buyurtmalar ro'yxati va holat filtrlari."""
    status_filter = request.args.get('status', '').strip()
    search = request.args.get('q', '').strip()

    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT o.*, u.full_name as user_name, u.phone as user_phone,
               (SELECT COUNT(*) FROM order_items WHERE order_id = o.id) as items_count
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND o.status = ?"
        params.append(status_filter)

    if search:
        query += " AND (o.order_number LIKE ? OR u.full_name LIKE ? OR u.phone LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " ORDER BY o.created_at DESC"

    cursor.execute(query, params)
    orders = [dict(row) for row in cursor.fetchall()]

    return render_template(
        'admin/orders.html',
        orders=orders,
        current_status=status_filter,
        current_search=search
    )

@admin_bp.route('/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id: int):
    """Buyurtma tafsilotlari va tarkibi."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.*, u.full_name as user_name, u.phone as user_phone, u.address as user_saved_address
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = ?
    """, (order_id,))
    order = cursor.fetchone()

    if not order:
        flash("Buyurtma topilmadi.", "danger")
        return redirect(url_for('admin.admin_orders'))

    cursor.execute("""
        SELECT oi.*, p.icon as product_icon, p.color_theme, p.sku
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    """, (order_id,))
    items = [dict(row) for row in cursor.fetchall()]

    return render_template('admin/order_detail.html', order=dict(order), items=items)

@admin_bp.route('/orders/update-status/<int:order_id>', methods=['POST'])
@admin_required
def admin_update_order_status(order_id: int):
    """Buyurtma holatini yangilash (yangi, to'langan, yo'lda, yetkazildi, bekor)."""
    new_status = request.form.get('status', '').strip()
    valid_statuses = ['yangi', 'to\'langan', 'yo\'lda', 'yetkazildi', 'bekor']

    if new_status not in valid_statuses:
        flash("Noto'g'ri buyurtma holati tanlandi.", "danger")
        return redirect(request.referrer or url_for('admin.admin_orders'))

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Agar buyurtma bekor qilinsa, ombor zaxirasini qaytarish
        if new_status == 'bekor':
            cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
            current_order = cursor.fetchone()
            if current_order and current_order['status'] != 'bekor':
                cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
                items = cursor.fetchall()
                for item in items:
                    cursor.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (item['quantity'], item['product_id']))

        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        conn.commit()
        flash(f"Buyurtma holati '{new_status}' ga o'zgartirildi.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Holatni o'zgartirishda xatolik: {str(e)}", "danger")

    return redirect(request.referrer or url_for('admin.admin_orders'))

@admin_bp.route('/promos', methods=['GET', 'POST'])
@admin_required
def admin_promos():
    """Promokodlar boshqaruvi: yangi qo'shish va ro'yxat."""
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            code = request.form.get('code', '').strip().upper()
            discount_type = request.form.get('discount_type', 'fixed')
            discount_value = request.form.get('discount_value', type=int) or 0
            min_order_amount = request.form.get('min_order_amount', type=int) or 0
            usage_limit = request.form.get('usage_limit', type=int) or 100
            valid_until = request.form.get('valid_until', '2026-12-31')

            if not code or discount_value <= 0:
                flash("Promokod nomi va chegirma miqdorini to'g'ri kiriting.", "danger")
            else:
                try:
                    cursor.execute("""
                        INSERT INTO promo_codes (code, discount_type, discount_value, min_order_amount, usage_limit, valid_until, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, 1)
                    """, (code, discount_type, discount_value, min_order_amount, usage_limit, valid_until))
                    conn.commit()
                    flash(f"'{code}' promokodi muvaffaqiyatli yaratildi!", "success")
                except Exception as e:
                    conn.rollback()
                    flash(f"Promokod qo'shishda xatolik (balki bunday kod mavjuddir): {str(e)}", "danger")

        elif action == 'toggle':
            promo_id = request.form.get('promo_id', type=int)
            cursor.execute("UPDATE promo_codes SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (promo_id,))
            conn.commit()
            flash("Promokod holati o'zgartirildi.", "info")

        elif action == 'delete':
            promo_id = request.form.get('promo_id', type=int)
            cursor.execute("DELETE FROM promo_codes WHERE id = ?", (promo_id,))
            conn.commit()
            flash("Promokod o'chirildi.", "warning")

        return redirect(url_for('admin.admin_promos'))

    cursor.execute("SELECT * FROM promo_codes ORDER BY id DESC")
    promos = [dict(row) for row in cursor.fetchall()]

    return render_template('admin/promos.html', promos=promos)

@admin_bp.route('/users')
@admin_required
def admin_users():
    """Foydalanuvchilar va sotuvchilar ro'yxati."""
    search = request.args.get('q', '').strip()
    role_filter = request.args.get('role', '').strip()

    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT u.*,
               (SELECT COUNT(*) FROM orders WHERE user_id = u.id) as orders_count,
               (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE user_id = u.id AND status != 'bekor') as total_spent
        FROM users u
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (u.full_name LIKE ? OR u.phone LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term])

    if role_filter:
        query += " AND u.role = ?"
        params.append(role_filter)

    query += " ORDER BY u.id DESC"

    cursor.execute(query, params)
    users = [dict(row) for row in cursor.fetchall()]

    return render_template('admin/users.html', users=users, current_search=search, current_role=role_filter)