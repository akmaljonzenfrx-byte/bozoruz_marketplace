import sqlite3
import os
import hashlib
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bozoruz.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_password(password: str) -> str:
    salt = "BozorUz_Secure_2025"
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def check_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'customer',
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        icon TEXT NOT NULL,
        bg_gradient TEXT DEFAULT 'from-blue-500 to-indigo-600'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sellers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        rating REAL DEFAULT 4.9,
        reviews_count INTEGER DEFAULT 120,
        phone TEXT,
        description TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        slug TEXT UNIQUE,
        category_id INTEGER NOT NULL,
        seller_id INTEGER NOT NULL,
        price INTEGER NOT NULL,
        old_price INTEGER,
        discount_percent INTEGER DEFAULT 0,
        stock INTEGER DEFAULT 10,
        rating REAL DEFAULT 4.8,
        reviews_count INTEGER DEFAULT 0,
        sales_count INTEGER DEFAULT 0,
        badge TEXT,
        icon_svg TEXT,
        gradient_theme TEXT,
        description TEXT,
        specifications TEXT,
        variants TEXT,
        is_flash_sale INTEGER DEFAULT 0,
        is_featured INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
        FOREIGN KEY (seller_id) REFERENCES sellers(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        customer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        total_price INTEGER NOT NULL,
        discount_amount INTEGER DEFAULT 0,
        final_price INTEGER NOT NULL,
        promo_code TEXT,
        status TEXT DEFAULT 'yangi',
        items_json TEXT NOT NULL,
        installment_months INTEGER DEFAULT 0,
        monthly_payment INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS promo_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        discount_percent INTEGER NOT NULL,
        min_amount INTEGER DEFAULT 0,
        max_discount INTEGER DEFAULT 500000,
        is_active INTEGER DEFAULT 1
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS banners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        subtitle TEXT,
        badge TEXT,
        btn_text TEXT DEFAULT 'Xarid qilish',
        link TEXT DEFAULT '/catalog',
        bg_gradient TEXT NOT NULL,
        icon_type TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        phone TEXT NOT NULL,
        target_price INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

def seed_initial_data():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    admin_pass = hash_password("admin123")
    cursor.execute("""
    INSERT INTO users (name, phone, password_hash, role, address)
    VALUES (?, ?, ?, ?, ?)
    """, ("Boshqaruvchi Admin", "+998901234567", admin_pass, "admin", "Toshkent shahri, Amir Temur ko'chasi 14-uy"))

    customer_pass = hash_password("123456")
    cursor.execute("""
    INSERT INTO users (name, phone, password_hash, role, address)
    VALUES (?, ?, ?, ?, ?)
    """, ("Davron Karimov", "+998935557788", customer_pass, "customer", "Samarqand sh., Registon ko'chasi 21-uy"))

    sellers = [
        ("TechPro Uzbekistan", 4.95, 480, "+998712001122", "Eng zamonaviy smartfonlar va gadjetlarning rasmiy yetkazib beruvchisi"),
        ("Elegant Moda & Style", 4.88, 312, "+998712003344", "Turkiya va Yevropadan keltirilgan sifatli kiyim-kechak do'koni"),
        ("EcoComfort Home", 4.92, 225, "+998712005566", "Uy va qulaylik uchun ekologik toza ro'zg'or mahsulotlari")
    ]
    cursor.executemany("""
    INSERT INTO sellers (name, rating, reviews_count, phone, description)
    VALUES (?, ?, ?, ?, ?)
    """, sellers)

    categories = [
        ("Elektronika", "elektronika", "phone-portrait-outline", "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)"),
        ("Kiyim-kechak", "kiyim-kechak", "shirt-outline", "linear-gradient(135deg, #ec4899 0%, #f43f5e 100%)"),
        ("Uy-ro'zg'or", "uy-rozgor", "home-outline", "linear-gradient(135deg, #0ea5e9 0%, #22c55e 100%)"),
        ("Go'zallik va parvarish", "gozallik", "sparkles-outline", "linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)"),
        ("Bolalar dunyosi", "bolalar", "balloon-outline", "linear-gradient(135deg, #14b8a6 0%, #06b6d4 100%)"),
        ("Sport va turizm", "sport", "fitness-outline", "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)"),
        ("Oziq-ovqat", "oziq-ovqat", "fast-food-outline", "linear-gradient(135deg, #84cc16 0%, #10b981 100%)"),
        ("Kitoblar", "kitoblar", "book-outline", "linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)")
    ]
    cursor.executemany("""
    INSERT INTO categories (name, slug, icon, bg_gradient)
    VALUES (?, ?, ?, ?)
    """, categories)

    banners = [
        (
            "Yozgi Katta Yangilanish",
            "Barcha elektronika va noutbuklarga 35% gacha imtiyozli chegirma",
            "Katta chegirma",
            "Katalogni ko'rish",
            "/catalog?category=elektronika",
            "linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%)",
            "laptop"
        ),
        (
            "Foizsiz Muddatli To'lov",
            "Orzuingizdagi tovarlarni 3, 6 va 12 oyga ustamasiz xarid qiling",
            "0-0-12 Aksiya",
            "Batafsil hisoblash",
            "/catalog",
            "linear-gradient(135deg, #059669 0%, #10b981 50%, #06b6d4 100%)",
            "card"
        ),
        (
            "Eksklyuziv Moda To'plami",
            "Turkiya brendlaridan yangi mavsum kiyimlari keldi",
            "Yangi to'plam",
            "Tanlash",
            "/catalog?category=kiyim-kechak",
            "linear-gradient(135deg, #d97706 0%, #ea580c 50%, #e11d48 100%)",
            "bag"
        )
    ]
    cursor.executemany("""
    INSERT INTO banners (title, subtitle, badge, btn_text, link, bg_gradient, icon_type)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, banners)

    promos = [
        ("BOZORUZ10", 10, 150000, 100000, 1),
        ("SUPER2025", 15, 300000, 250000, 1),
        ("YANGI50K", 5, 50000, 50000, 1),
        ("BAHOR20", 20, 500000, 400000, 1)
    ]
    cursor.executemany("""
    INSERT INTO promo_codes (code, discount_percent, min_amount, max_discount, is_active)
    VALUES (?, ?, ?, ?, ?)
    """, promos)

    raw_products = [
        # 1. Elektronika (1-8)
        (
            "Smartfon UltraPro 15 Max 256GB Titanium",
            "elektronika-smartfon-ultrapro-15-max",
            1, 1, 14200000, 16500000, 14, 25, 4.95, 142, 380, "XIT SAVDO",
            "phone", "linear-gradient(135deg, #1e293b, #0f172a)",
            "Eng so'nggi flagman protsessor, 120Hz Super AMOLED ekrani va yuqori darajadagi titan korpusi bilan uzoq yillik unumdorlikni kafolatlaydi.",
            json.dumps({"Xotira": "256 GB", "Tezkor xotira": "8 GB RAM", "Kamera": "48 MP + 12 MP + 12 MP", "Batareya": "4422 mA/soat", "Kafolat": "1 yil rasmiy"}),
            json.dumps({"Rang": ["Tabiiy titan", "Moviy titan", "Qora grafit"], "Xotira": ["256GB", "512GB"]}),
            1, 1
        ),
        (
            "Noutbuk NovaBook Pro 15.6 Core i7 16GB/512GB",
            "elektronika-noutbuk-novabook-pro-15",
            1, 1, 8900000, 10500000, 15, 12, 4.88, 64, 120, "TAVSIYA",
            "laptop", "linear-gradient(135deg, #334155, #1e293b)",
            "Dasturlash, ofis ishlari va grafik dizayn uchun yengil alyuminiy korpusli yuqori tezlikdagi noutbuk.",
            json.dumps({"Protsessor": "Intel Core i7-1355U", "Ekran": "15.6 FHD IPS", "RAM": "16 GB DDR4", "SSD": "512 GB NVMe", "Vazni": "1.65 kg"}),
            json.dumps({"Rang": ["Kumushrang", "Kosmik kulrang"]}),
            0, 1
        ),
        (
            "Simsiz quloqchin AirBeats SoundPro ANC",
            "elektronika-simsiz-quloqchin-airbeats-soundpro",
            1, 1, 480000, 650000, 26, 45, 4.82, 210, 750, "CHEGIRMA",
            "headset", "linear-gradient(135deg, #0284c7, #0369a1)",
            "Faol shovqinni so'ndirish texnologiyasi (ANC), tiniq baslar va 36 soatgacha to'xtovsiz ishlash quvvati.",
            json.dumps({"Bluetooth": "5.3", "Ishlash vaqti": "36 soat (keys bilan)", "Shovqin bostirish": "Ha, faol ANC", "Mikrofon": "Har quloqchinda 2 tadan"}),
            json.dumps({"Rang": ["Oq marvarid", "Mat qora"]}),
            1, 1
        ),
        (
            "Aqlli soat SmartFit Band Watch Series 9",
            "elektronika-aqlli-soat-smartfit-band-watch-9",
            1, 1, 399000, 520000, 23, 30, 4.79, 95, 420, "YANGI",
            "watch", "linear-gradient(135deg, #475569, #334155)",
            "Puls, qondagi kislorod, uyqu fazalari va 100 dan ortiq sport rejimlarini aniq o'lchovchi aqlli soat.",
            json.dumps({"Ekran": "1.92 dyuym AMOLED", "Suvdan himoya": "IP68 / 5ATM", "Batareya": "10 kungacha", "NFC": "Mavjud"}),
            json.dumps({"Kamar rangi": ["Qora", "To'q ko'k", "Pushti"]}),
            0, 1
        ),
        (
            "Portativ tashqi akkumulyator PowerCore 20 000 mAh 65W",
            "elektronika-powercore-20000-mah",
            1, 1, 320000, 420000, 24, 60, 4.91, 180, 890, "XIT SAVDO",
            "battery-charging", "linear-gradient(135deg, #1e293b, #0f172a)",
            "Noutbuk, planshet va smartfonlarni ultra tez quvvatlovchi zamonaviy 65W PD zaryadlovchi.",
            json.dumps({"Sig'imi": "20000 mA/soat", "Maksimal quvvat": "65W PD", "Portlar": "2x Type-C, 1x USB-A", "Vazni": "410 g"}),
            json.dumps({"Rang": ["Qora", "Kumush"]}),
            1, 0
        ),
        (
            "Bluetooth akustik karnay SoundBoom 30W Suv o'tkazmas",
            "elektronika-soundboom-30w-dinamik",
            1, 1, 350000, 490000, 29, 20, 4.74, 52, 210, "CHEGIRMA",
            "musical-notes", "linear-gradient(135deg, #0d9488, #0f766e)",
            "Kuchli 30W stereo bas va IPX7 suv o'tkazmaslik darajasi. Tabiat qo'ynidagi dam olishlar uchun ideal.",
            json.dumps({"Quvvat": "30W Stereo", "Batareya": "12 soat", "Himoya": "IPX7 suvga chidamli", "Bluetooth": "5.2"}),
            json.dumps({"Rang": ["Qora", "Harbiy yashil", "Qizil"]}),
            1, 0
        ),
        (
            "Ultra HD 4K Web-kamera ProCam Studio mikrofonli",
            "elektronika-procam-studio-web-camera",
            1, 1, 280000, 390000, 28, 18, 4.86, 39, 140, "YANGI",
            "videocam", "linear-gradient(135deg, #64748b, #475569)",
            "Onlayn darslar, konferensiyalar va strimlar uchun shovqinni kamaytiruvchi ikki yoqlama mikrofonga ega.",
            json.dumps({"Ruxsat": "3840x2160 (4K)", "Kadr tezligi": "30 fps / 60 fps (1080p)", "Fokus": "Avtofokus", "Ulanish": "USB Plug & Play"}),
            json.dumps({"Rang": ["Qora"]}),
            0, 0
        ),
        (
            "Mexanik o'yin klaviaturasi RGB ProGamer Red Switch",
            "elektronika-mechanic-keyboard-progamer",
            1, 1, 440000, 580000, 24, 15, 4.89, 78, 310, "XIT SAVDO",
            "hardware-chip", "linear-gradient(135deg, #7c3aed, #6d28d9)",
            "Qizil tezkor mexanik svitchlar, 16.8 million rangli moslashtiriladigan RGB yoritgich.",
            json.dumps({"Svitch turi": "Red Linear Switch", "Tugmalar soni": "87 ta (TKL)", "Kabel": "Olinadigan Type-C o'rilgan", "Resurs": "50 mln bosish"}),
            json.dumps({"Rang": ["Qora korpus", "Oq korpus"]}),
            1, 1
        ),

        # 2. Kiyim-kechak (9-16)
        (
            "Erkaklar klassik paxta ko'ylagi Slim Fit Premium",
            "kiyim-erkaklar-koylak-slim-fit-premium",
            2, 2, 220000, 310000, 29, 40, 4.85, 115, 540, "XIT SAVDO",
            "shirt", "linear-gradient(135deg, #0369a1, #0284c7)",
            "100% tabiiy paxtadan tayyorlangan nafas oluvchi, dazmollanishi oson oliy sifatli erkaklar ko'ylagi.",
            json.dumps({"Tarkibi": "100% Paxta", "Fason": "Slim Fit", "Ishlab chiqarilgan": "Turkiya", "Mavsum": "Barcha fasllar"}),
            json.dumps({"O'lcham": ["M (48)", "L (50)", "XL (52)", "XXL (54)"], "Rang": ["Oq", "Havorang", "Qora"]}),
            0, 1
        ),
        (
            "Ayollar nafis baxmal kechki libosi 'Zarafshon'",
            "kiyim-ayollar-baxmal-kechki-libos",
            2, 2, 450000, 600000, 25, 15, 4.93, 44, 160, "TAVSIYA",
            "female", "linear-gradient(135deg, #9d174d, #be185d)",
            "Kechki to'y va bayramlar uchun mo'ljallangan nozik bichimli, nafis va jozibador uzun libos.",
            json.dumps({"Mato": "Qirollik baxmali", "Uzunligi": "To'piqqacha", "Astar": "Ipak astar", "Tozalash": "Kimyoviy tozalash"}),
            json.dumps({"O'lcham": ["38 (S)", "40 (M)", "42 (L)"], "Rang": ["Zumrad yashil", "Yoqut qizil", "Qora"]}),
            1, 0
        ),
        (
            "Erkaklar sport kostyumi qalin trikotaj Hoodie Set",
            "kiyim-erkaklar-sport-kostyumi-hoodie",
            2, 2, 380000, 490000, 22, 28, 4.80, 86, 390, "CHEGIRMA",
            "body", "linear-gradient(135deg, #374151, #1f2937)",
            "Kuz va bahor mavsumi uchun qulay kapyushonli xudi va shim to'plami.",
            json.dumps({"Mato": "Uch ipli futer paxta", "Model": "Oversize", "Zanjir": "Sifatli YKK", "Fasl": "Bahor/Kuz"}),
            json.dumps({"O'lcham": ["S", "M", "L", "XL", "2XL"], "Rang": ["Kulrang", "Qora", "Zaytun yashil"]}),
            0, 1
        ),
        (
            "Ayollar qishki issiq jaketi 'EcoDown' termal",
            "kiyim-ayollar-jaket-ecodown",
            2, 2, 620000, 850000, 27, 20, 4.89, 73, 280, "XIT SAVDO",
            "cloudy", "linear-gradient(135deg, #475569, #334155)",
            "Yengil va sovuq o'tkazmaydigan eko-pat to'ldiruvchili zamonaviy ayollar kurtkasi.",
            json.dumps({"Tashqi qatlam": "Suv o'tkazmaydigan mato", "To'ldiruvchi": "Eko-pat 300g", "Kapyushon": "Yechiladigan mo'ynali", "Harorat": "-20°C gacha"}),
            json.dumps({"O'lcham": ["M", "L", "XL"], "Rang": ["Krem oq", "Qora", "Karamel"]}),
            1, 0
        ),
        (
            "Erkaklar klassik qora jinsi shimi Denim Flex",
            "kiyim-erkaklar-jinsi-shimi-denim-flex",
            2, 2, 240000, 320000, 25, 50, 4.77, 98, 460, "CHEGIRMA",
            "layers", "linear-gradient(135deg, #1e3a8a, #1e40af)",
            "Cho'ziluvchan elastan qo'shilgan mustahkam denim mato, har kungi qulay yurish uchun.",
            json.dumps({"Tarkibi": "98% Paxta, 2% Spandeks", "Bichim": "Regular Tapered", "Mavsum": "Barcha mavsum"}),
            json.dumps({"O'lcham (Bel)": ["30", "32", "34", "36", "38"], "Rang": ["To'q ko'k", "Klassik qora"]}),
            0, 0
        ),
        (
            "Yozgi nafis shifon ko'ylak gulli print bilan",
            "kiyim-yozgi-nafis-shifon-koylak",
            2, 2, 290000, 390000, 26, 35, 4.88, 57, 230, "YANGI",
            "flower", "linear-gradient(135deg, #f43f5e, #e11d48)",
            "Engil nafas oluvchi havodor shifon mato, bel qismida elastik tasma va nafis kamarga ega.",
            json.dumps({"Mato": "Fransuz shifoni", "Astar": "Paxta astar", "Uzunligi": "Midi", "Qo'l uzunligi": "3/4"}),
            json.dumps({"O'lcham": ["S", "M", "L"], "Rang": ["Pushti gul", "Moviy gul", "Sariq gul"]}),
            1, 1
        ),
        (
            "Erkaklar charm kamar to'plami metall tokali",
            "kiyim-erkaklar-charm-kamar-toplami",
            2, 2, 130000, 180000, 28, 70, 4.83, 145, 620, "XIT SAVDO",
            "ribbon", "linear-gradient(135deg, #78350f, #92400e)",
            "100% tabiiy buqa charmidan tayyorlangan, zanglamaydigan po'lat qisqichli nafis erkaklar kamari.",
            json.dumps({"Material": "100% Tabiiy charm", "Eni": "3.5 sm", "Uzunligi": "125 sm (kesib qisqartirish mumkin)", "Toka": "Avtomat qisqich"}),
            json.dumps({"Rang": ["Klassik qora", "To'q jigarrang"]}),
            0, 0
        ),
        (
            "Paxtali paypoqlar to'plami (10 juftlik to'plam)",
            "kiyim-paxtali-paypoqlar-toplami-10-juft",
            2, 2, 85000, 120000, 29, 100, 4.90, 310, 1250, "CHEGIRMA",
            "gift", "linear-gradient(135deg, #4b5563, #374151)",
            "Nafas oluvchi, terlatmaydigan va hidga qarshi tabiiy taroqli paxtadan tayyorlangan paypoqlar.",
            json.dumps({"Tarkibi": "90% Paxta, 8% Poliamid, 2% Likra", "Juft soni": "10 juft", "O'lchami": "Universal (40-44)"}),
            json.dumps({"Rang to'plami": ["Barcha qora", "Aralash (qora, kulrang, oq)", "Barcha oq"]}),
            1, 0
        ),

        # 3. Uy-ro'zg'or (17-24)
        (
            "Robot changyutgich CleanMaster X-Smart Lidar nam tozalash",
            "uy-robot-changyutgich-cleanmaster-x",
            3, 3, 2650000, 3400000, 22, 15, 4.92, 110, 310, "XIT SAVDO",
            "disc", "linear-gradient(135deg, #0284c7, #0369a1)",
            "Lidar lazer navigatsiyasi, xaritalash, bir vaqtning o'zida ham quruq ham nam tozalash funksiyasi.",
            json.dumps({"So'rish kuchi": "4000 Pa", "Suv idishi": "300 ml", "Chang idishi": "450 ml", "Mobil ilova": "Mavjud (Android/iOS)"}),
            json.dumps({"Rang": ["Mat qora", "Yaltiroq oq"]}),
            1, 1
        ),
        (
            "Induksion elektr choynak SmartKettle 1.7L harorat nazorati",
            "uy-smartkettle-elektr-choynak-harorat",
            3, 3, 290000, 390000, 26, 35, 4.85, 87, 430, "CHEGIRMA",
            "cafe", "linear-gradient(135deg, #059669, #047857)",
            "Zanglamas po'lat 304, haroratni 40-100 gradus oralig'ida saqlab turish funksiyasiga ega sensorli choynak.",
            json.dumps({"Sig'imi": "1.7 litr", "Quvvati": "2200 W", "Material": "Oziq-ovqat po'lati 304", "Avto-o'chish": "Mavjud"}),
            json.dumps({"Rang": ["Qora mat", "Oq sadaf"]}),
            0, 1
        ),
        (
            "Granit qoplamali qozonlar to'plami EcoGranite 7 dona",
            "uy-granit-qozonlar-toplami-ecogranite",
            3, 3, 890000, 1200000, 26, 18, 4.94, 94, 280, "TAVSIYA",
            "restaurant", "linear-gradient(135deg, #475569, #334155)",
            "Ovqat yopishmaydigan ekologik toza 5 qavatli granit qoplama. Har qanday turdagi plitalarga mos.",
            json.dumps({"Material": "Quyma alyuminiy + Granit", "To'plam": "3 ta qozon + 1 skovoroda + 3 qopqoq", "Idish yuvish mashinasi": "Mumkin"}),
            json.dumps({"Rang": ["Kulrang tosh", "Jigarrang marmar"]}),
            1, 0
        ),
        (
            "Havo tozalovchi va namlagich PureAir Ionic 45 kv.m",
            "uy-pureair-havo-tozalovchi-namlagich",
            3, 3, 750000, 990000, 24, 22, 4.87, 56, 190, "YANGI",
            "leaf", "linear-gradient(135deg, #0d9488, #0f766e)",
            "HEPA H13 filtrli havo tozalagich, chang, allergen va yoqimsiz hidlarni 99.97% ga yo'qotadi.",
            json.dumps({"Filtr turi": "HEPA H13 + Ko'mir filtr", "Maydoni": "45 kv.m", "Shovqin darajasi": "24 dB (Tungi rejim)", "Namlagich": "Ultratovushli"}),
            json.dumps({"Rang": ["Oq"]}),
            0, 1
        ),
        (
            "Yumshoq ortopedik matras qoplamasi Topper Memory Foam",
            "uy-ortopedik-matras-topper-memory",
            3, 3, 420000, 580000, 28, 25, 4.81, 41, 130, "CHEGIRMA",
            "bed", "linear-gradient(135deg, #6366f1, #4f46e5)",
            "Uyqu sifatini yaxshilovchi, xotiraga ega qalin yumshoq qatlam. Bel va orqa og'riqlarining oldini oladi.",
            json.dumps({"Material": "Memory Foam 5 sm", "G'ilof": "Yechib yuviladigan jakkard", "Gipoallergen": "Ha"}),
            json.dumps({"O'lcham": ["160x200 sm", "180x200 sm", "90x200 sm"]}),
            0, 0
        ),
        (
            "Sensorli avtomatik axlat qutisi SmartTrash 15L",
            "uy-smarttrash-sensorli-axlat-qutisi",
            3, 3, 210000, 290000, 28, 30, 4.78, 62, 240, "YANGI",
            "trash", "linear-gradient(135deg, #64748b, #475569)",
            "Qo'l yaqinlashtirilganda 0.3 soniyada jim ochiluvchi, hid tarqalishini to'suvchi germetik qopqoq.",
            json.dumps({"Hajmi": "15 Litr", "Sensor masofasi": "25 sm", "Quvvat": "4x AA batareya yoki USB zaryad"}),
            json.dumps({"Rang": ["Oq", "To'q kulrang"]}),
            1, 0
        ),
        (
            "Mikrotola vanna sochiqlari to'plami (3 dona katta)",
            "uy-mikrotola-vanna-sochiqlari-toplami",
            3, 3, 160000, 220000, 27, 45, 4.88, 89, 410, "XIT SAVDO",
            "water", "linear-gradient(135deg, #06b6d4, #0891b2)",
            "Suvni darhol o'ziga tortuvchi, yuvilganda tushmaydigan va yumshoqligini yo'qotmaydigan bambuk tolali sochiqlar.",
            json.dumps({"O'lcham": "70x140 sm (3 dona)", "Mato": "Bambuk va mikrotola", "Zichlik": "550 g/m²"}),
            json.dumps({"Rang": ["Kulrang-ko'k-krem", "Pushti-binafsha-oq"]}),
            0, 0
        ),
        (
            "Oshxona pichoqlari to'plami stend bilan (6 dona po'lat)",
            "uy-oshxona-pichoqlari-toplami-stend",
            3, 3, 270000, 360000, 25, 30, 4.90, 75, 320, "TAVSIYA",
            "cutlery", "linear-gradient(135deg, #334155, #1e293b)",
            "Yuqori uglerodli zanglamas po'latdan lazer bilan charxlangan o'ta o'tkir professional pichoqlar.",
            json.dumps({"Po'lat navi": "X30Cr13 zanglamas", "To'plam": "Shef pichoq, non pichog'i, go'sht pichog'i, stend", "Charx": "To'plamda charxlagich bor"}),
            json.dumps({"Stend rangi": ["Yog'och rang", "Qora akril"]}),
            1, 1
        ),

        # 4. Go'zallik va parvarish (25-32)
        (
            "Professional fen-styler Dyson uslubidagi 5-in-1",
            "gozallik-professional-fen-styler-5in1",
            4, 2, 590000, 850000, 31, 24, 4.89, 130, 580, "XIT SAVDO",
            "sparkles", "linear-gradient(135deg, #db2777, #be185d)",
            "Sochlarni shikastlamasdan quritish, to'lqin qilish va tekislash uchun aerodinamik 5 ta nozul to'plami.",
            json.dumps({"Quvvati": "1200W", "Ionizatsiya": "Mavjud", "Tezliklar soni": "3 bosqichli", "Kabel uzunligi": "2 metr aylanuvchi"}),
            json.dumps({"Rang": ["Kulrang/Fuksiya", "Ko'k/Tilla"]}),
            1, 1
        ),
        (
            "Yuzni chuqur tozalovchi ultratovushli skrubber apparati",
            "gozallik-ultratovushli-skrubber-apparat",
            4, 2, 175000, 250000, 30, 40, 4.75, 68, 290, "CHEGIRMA",
            "fitness", "linear-gradient(135deg, #ec4899, #db2777)",
            "Uy sharoitida qora nuqtalar, ajinlar va ortiqcha yog'lanishni yo'qotuvchi salon darajasidagi qurilma.",
            json.dumps({"Rejimlar": "Tozalash, namlash, lifting", "Chastota": "24 000 Hz", "Zaryad": "USB orqali 2 soat"}),
            json.dumps({"Rang": ["Oq", "Pushti"]}),
            0, 0
        ),
        (
            "Tabiiy efir moylari to'plami 100% organik (6 x 10ml)",
            "gozallik-tabiiy-efir-moylari-toplami",
            4, 2, 120000, 160000, 25, 50, 4.93, 85, 340, "TAVSIYA",
            "leaf", "linear-gradient(135deg, #10b981, #059669)",
            "Lavanda, choy daraxti, evkalipt, apelsin, yalpiz va bibariya efir moylari. Aroma diffuzer va massaj uchun.",
            json.dumps({"Hajmi": "6 dona x 10 ml", "Tarkib": "100% toza efir moyi", "Sertifikat": "Organik ISO"}),
            json.dumps({"To'plam": ["Standart 6 talik", "Tinchlantiruvchi to'plam"]}),
            1, 0
        ),
        (
            "Koreya gialuron kislotali namlantiruvchi yuz zardobi",
            "gozallik-koreya-gialuron-zardobi",
            4, 2, 95000, 140000, 32, 65, 4.87, 192, 850, "XIT SAVDO",
            "water", "linear-gradient(135deg, #0ea5e9, #0284c7)",
            "Terining chuqur qatlamlarini namlantiradi, mayda ajinlarni tekislaydi va yuzga sog'lom jilo bag'ishlaydi.",
            json.dumps({"Hajmi": "50 ml", "Faol modda": "Gialuron kislotasi 2%", "Ishlab chiqarilgan": "Janubiy Koreya"}),
            json.dumps({"Turi": ["Kunduzgi zardob", "Tungi zardob"]}),
            0, 1
        ),
        (
            "Professional soqol va soch olish mashinkasi Trimmer VGR",
            "gozallik-soqol-trimmer-vgr",
            4, 2, 185000, 260000, 29, 35, 4.83, 140, 610, "CHEGIRMA",
            "cut", "linear-gradient(135deg, #b45309, #92400e)",
            "Zanglamaydigan T-shaklidagi pichoqlar, litiy batareya va LED zaryad ko'rsatkichi bilan jihozlangan metal korpus.",
            json.dumps({"Pichoq materiali": "Titan po'lat", "Batareya": "120 daqiqa ishlash", "Nozullar": "1, 2, 3 mm", "Zaryad": "USB Type-C"}),
            json.dumps({"Rang": ["Bronza vintage", "Qora metal"]}),
            1, 0
        ),
        (
            "Yuz va tana uchun quyoshdan himoyalovchi krem SPF 50+",
            "gozallik-quyoshdan-himoyalovchi-krem-spf50",
            4, 2, 89000, 130000, 32, 70, 4.90, 220, 940, "XIT SAVDO",
            "sunny", "linear-gradient(135deg, #f59e0b, #d97706)",
            "UVA va UVB nurlaridan maksimal darajada himoya qiladi, terida oq iz qoldirmaydi, makiyaj ostiga mos.",
            json.dumps({"Himoya darajasi": "SPF 50+ PA++++", "Hajmi": "70 ml", "Moy qoldirmaslik": "Suv asosida"}),
            json.dumps({"Hajm": ["70 ml", "120 ml"]}),
            0, 0
        ),
        (
            "Elektr tish cho'tkasi Sonic Clean 4 ta almashtirish nozuli",
            "gozallik-elektr-tish-chotkasi-sonic",
            4, 2, 160000, 230000, 30, 45, 4.86, 105, 470, "YANGI",
            "flash", "linear-gradient(135deg, #06b6d4, #0891b2)",
            "Daqiqasiga 40 000 ultratovushli tebranish, tish toshlari va qorayishlarni xavfsiz tozalaydi.",
            json.dumps({"Tebranish": "40 000 / daqiqa", "Rejimlar": "5 xil rejim", "Batareya": "Bir zaryad bilan 45 kun", "Himoya": "IPX7 suv o'tkazmas"}),
            json.dumps({"Rang": ["Oq sadaf", "Pushti marvarid", "Qora mat"]}),
            1, 1
        ),
        (
            "Fransuz parfyumeriya suvi 'Amour Royale' 100 ml",
            "gozallik-parfyumeriya-amour-royale",
            4, 2, 340000, 480000, 29, 25, 4.94, 88, 320, "TAVSIYA",
            "flask", "linear-gradient(135deg, #9333ea, #7e22ce)",
            "Bargamot, oq mushk va vanil notalaridan iborat uzoq saqlanuvchi sehrli shleyfli xushbo'y ifor.",
            json.dumps({"Turi": "Eau de Parfum", "Hajmi": "100 ml", "Chidamlilik": "24 soatgacha", "Ishlab chiqarilgan": "Fransiya texnologiyasi"}),
            json.dumps({"Turi": ["Erkaklar uchun", "Ayollar uchun"]}),
            0, 1
        ),

        # 5. Bolalar dunyosi (33-40)
        (
            "Interaktiv aqlli robot o'yinchoq pult va ovozli boshqaruv",
            "bolalar-aqlli-robot-oyinchoq",
            5, 3, 240000, 320000, 25, 20, 4.88, 64, 230, "XIT SAVDO",
            "game-controller", "linear-gradient(135deg, #3b82f6, #2563eb)",
            "Qo'shiq kuylaydi, raqsga tushadi, hikoyalar aytadi va imo-ishoralarga javob qaytaradi.",
            json.dumps({"Yoshi": "3 yoshdan katta", "Pult masofasi": "15 metr", "Material": "Xavfsiz ABS plastik", "Zaryad": "Akkumulyatordan"}),
            json.dumps({"Rang": ["Oq-moviy", "Oq-qizil"]}),
            1, 0
        ),
        (
            "Bolalar konstruktori 'Kosmik kema va baza' 850 bo'lak",
            "bolalar-konstruktor-kosmik-kema",
            5, 3, 210000, 290000, 28, 30, 4.91, 79, 340, "TAVSIYA",
            "cube", "linear-gradient(135deg, #6366f1, #4f46e5)",
            "Mantiqiy fikrlash va nozik motorikani rivojlantiruvchi sifatli bloklardan iborat konstruktor to'plami.",
            json.dumps({"Bo'laklar soni": "850 ta", "Muvofiqlik": "Standart bloklar bilan to'liq mos", "Yoshi": "6-14 yosh"}),
            json.dumps({"To'plam": ["Kosmik stansiya", "Qutqaruvchi baza"]}),
            0, 1
        ),
        (
            "Ko'p funksiyali yengil bolalar aravachasi 'BabyTravel Fold'",
            "bolalar-aravacha-babytravel-fold",
            5, 3, 980000, 1300000, 25, 12, 4.95, 52, 170, "XIT SAVDO",
            "car", "linear-gradient(135deg, #0ea5e9, #0284c7)",
            "Bir qo'l bilan 3 soniyada ixcham buklanuvchi, samolyot saloniga qo'l yuki sifatida olishga ruxsat etilgan.",
            json.dumps({"Vazni": "6.2 kg", "Yuklama": "22 kg gacha", "Amortizatsiya": "4 ta g'ildirakda", "Komplekt": "Yomg'irpo'sh, savatcha, chivin to'ri"}),
            json.dumps({"Rang": ["To'q kulrang", "Havorang", "Zumrad yashil"]}),
            1, 1
        ),
        (
            "Bolalar uchun rasm chizish to'plami chamadonda 145 dona",
            "bolalar-rasm-chizish-toplami-145",
            5, 3, 150000, 210000, 29, 45, 4.82, 110, 520, "CHEGIRMA",
            "color-palette", "linear-gradient(135deg, #ec4899, #db2777)",
            "Floromasterlar, akvarel bo'yoqlar, pastel qalamlar va moyli bo'yoqlardan iborat nafis alyuminiy chamadoncha.",
            json.dumps({"Bo'laklar soni": "145 ta", "Korpus": "Alyuminiy chamadon", "Xavfsizlik": "Zaharsiz suv asosidagi bo'yoqlar"}),
            json.dumps({"Chamadon rangi": ["Moviy kosmos", "Pushti ertak"]}),
            0, 0
        ),
        (
            "Yumshoq ayiqcha PlushTeddy 100 sm ulkan sovg'a",
            "bolalar-yumshoq-ayiqcha-plushteddy-100sm",
            5, 3, 190000, 270000, 30, 25, 4.86, 95, 410, "YANGI",
            "heart", "linear-gradient(135deg, #f59e0b, #d97706)",
            "Gipoallergen tola bilan to'ldirilgan juda yumshoq, quchoqlash uchun ajoyib ulkan ayiq o'yinchoq.",
            json.dumps({"Balandligi": "100 sm", "Material": "Plush mikrotola", "To'ldiruvchi": "Holofayber", "Yuvilishi": "Kir yuvish mashinasiga mos"}),
            json.dumps({"Rang": ["Sut rang", "Karamel jigarrang", "Pushti"]}),
            1, 0
        ),
        (
            "Bolalar uchun magnitli yozuv va rasm plansheti 12 dyuym",
            "bolalar-magnitli-yozuv-plansheti-12",
            5, 3, 75000, 110000, 32, 60, 4.79, 148, 680, "CHEGIRMA",
            "create", "linear-gradient(135deg, #10b981, #059669)",
            "Ko'zga zarar yetkazmaydigan rangli LCD ekran. Bir tugma bilan ekranni tozalash va qulflash funksiyasi.",
            json.dumps({"Ekran o'lchami": "12 dyuym rangli", "Batareya": "CR2025 (1 yil yetadi)", "Qalam": "Stilus to'plamda"}),
            json.dumps({"Korpus rangi": ["Moviy", "Pushti", "Qora"]}),
            0, 0
        ),
        (
            "Bolalar velosipedi 16 dyuym qo'shimcha g'ildiraklari bilan",
            "bolalar-velosipedi-16-dyuym",
            5, 3, 680000, 890000, 24, 15, 4.90, 43, 140, "XIT SAVDO",
            "bicycle", "linear-gradient(135deg, #e11d48, #be123c)",
            "Mustahkam po'lat rama, zanjir himoyasi, qo'l tormozi va orqa mustahkamlovchi yordamchi g'ildiraklar.",
            json.dumps({"G'ildirak o'lchami": "16 dyuym", "Mos yosh": "4-7 yosh (100-120 sm)", "Tormoz": "Old va orqa qo'l tormozi"}),
            json.dumps({"Rang": ["Yorqin qizil", "Moviy moviy", "Yashil lime"]}),
            1, 1
        ),
        (
            "Bolalar ta'limiy plansheti alifbo va ertaklar bilan",
            "bolalar-talimiy-plansheti-uzb",
            5, 3, 140000, 195000, 28, 35, 4.84, 82, 330, "TAVSIYA",
            "school", "linear-gradient(135deg, #8b5cf6, #7c3aed)",
            "O'zbek va ingliz tillarida harflar, raqamlar, hayvonlar ovozi va bolalar qo'shiqlarini o'rgatuvchi planshet.",
            json.dumps({"Tillar": "O'zbekcha / Inglizcha", "Funksiyalar": "Viktorina, musiqa, talaffuz", "Batareya": "3x AAA"}),
            json.dumps({"Rang": ["Sariq", "Moviy"]}),
            0, 0
        ),

        # 6. Sport va turizm (41-48)
        (
            "Yig'iluvchi trenajyor yugurish yo'lakchasi HomeFit 2.5 HP",
            "sport-yugurish-yolakchasi-homefit",
            6, 1, 3850000, 4900000, 21, 8, 4.93, 38, 95, "XIT SAVDO",
            "walk", "linear-gradient(135deg, #0284c7, #0369a1)",
            "Kvartira uchun juda qulay, karavot yoki divan ostiga sig'adigan jim motorli zamonaviy yugurish yo'lakchasi.",
            json.dumps({"Dvigatel quvvati": "2.5 ot kuchi", "Maksimal tezlik": "1-12 km/soat", "Maksimal vazn": "110 kg", "Displey": "LED tezlik va kaloriya"}),
            json.dumps({"Rang": ["Qora titan", "Kumush kulrang"]}),
            1, 1
        ),
        (
            "Og'irligi sozlanuvchi gantellar to'plami 20 kg qutida",
            "sport-gantellar-toplami-20kg",
            6, 1, 320000, 420000, 24, 25, 4.87, 92, 380, "CHEGIRMA",
            "barbell", "linear-gradient(135deg, #374151, #1f2937)",
            "Xromlangan temir disklar va shtanga aylantiruvchi qulay oraliq ulagichli ko'p funksiyali to'plam.",
            json.dumps({"Umumiy og'irlik": "20 kg", "Material": "Xrom po'lat va rezinlashtirilgan tutqich", "Quti": "Plastik chamadon mavjud"}),
            json.dumps({"Variant": ["Standart 20 kg", "Kengaytirilgan 30 kg (+120 000 so'm)"]}),
            0, 1
        ),
        (
            "Suv o'tkazmaydigan sayohat chodiri (Palatka) 4 kishilik",
            "sport-sayohat-chodiri-palatka-4kishilik",
            6, 1, 390000, 520000, 25, 18, 4.89, 45, 160, "TAVSIYA",
            "bonfire", "linear-gradient(135deg, #059669, #047857)",
            "Tog' va tabiat bag'rida dam olish uchun shamolga chidamli karkasli, ikki qavatli tez yig'iluvchi chodir.",
            json.dumps({"Sig'imi": "3-4 kishi", "Suvga chidamlilik": "PU 3000 mm", "O'lchami": "210x210x140 sm", "Og'irligi": "3.1 kg"}),
            json.dumps({"Rang": ["O'rmon yashili", "Moviy"]}),
            1, 0
        ),
        (
            "Termos termokrujka zanglamas po'lat 1000 ml harorat saqlovchi",
            "sport-termos-1000ml-po'lat",
            6, 1, 140000, 195000, 28, 40, 4.84, 115, 490, "XIT SAVDO",
            "cafe", "linear-gradient(135deg, #0d9488, #0f766e)",
            "Issiq ichimliklarni 24 soat, sovuqni 36 soat ushlab turuvchi vakuumli devorga ega sayohat termosi.",
            json.dumps({"Hajmi": "1000 ml (1 litr)", "Material": "316 tibbiy zanglamas po'lat", "Qopqoq": "Piyola sifatida ishlatish mumkin"}),
            json.dumps({"Rang": ["Mat qora", "Harbiy zaytun", "Po'lat rang"]}),
            0, 0
        ),
        (
            "Fitnes va yoga uchun sirpanmaydigan gilamcha TPE 6mm",
            "sport-yoga-gilamcha-tpe-6mm",
            6, 1, 115000, 160000, 28, 55, 4.86, 78, 340, "CHEGIRMA",
            "body", "linear-gradient(135deg, #8b5cf6, #7c3aed)",
            "Ekologik toza TPE materiali, tizzalarni og'ritmaydigan optimal qalinlik va qulay yelkama tasma.",
            json.dumps({"O'lchami": "183 x 61 sm", "Qalinligi": "6 mm", "Material": "Ekologik TPE (hidsiz)", "Tekstura": "Sirpanishga qarshi ikki tomonlama"}),
            json.dumps({"Rang": ["Binafsha-pushti", "Moviy-ko'k", "Zangori-yashil"]}),
            1, 0
        ),
        (
            "Tog' velosipedi SportCross 27.5 Shimano 21 tezlik",
            "sport-tog-velosipedi-sportcross-27",
            6, 1, 1950000, 2500000, 22, 10, 4.92, 34, 85, "TAVSIYA",
            "bicycle", "linear-gradient(135deg, #ea580c, #c2410c)",
            "Alyuminiy yengil rama, old amortizator vilkasi, ishonchli diskli mexanik tormozlar.",
            json.dumps({"Rama materiali": "Alyuminiy qotishmasi 6061", "G'ildirak": "27.5 dyuym", "Uzatgich": "Shimano Tourney 21 tezlik", "Vazni": "14.5 kg"}),
            json.dumps({"Rang": ["Mat qora/Qizil", "To'q kulrang/Limon"]}),
            0, 1
        ),
        (
            "Sport sumkasi poyabzal bo'limi va suv o'tkazmaydigan cho'ntak",
            "sport-sumkasi-poyabzal-bolimli",
            6, 1, 135000, 190000, 29, 35, 4.80, 62, 290, "YANGI",
            "briefcase", "linear-gradient(135deg, #475569, #334155)",
            "Zal mashg'ulotlari va qisqa muddatli safarlar uchun poyabzal va ho'l sochiqni alohida saqlash bo'lmasi bor.",
            json.dumps({"Hajmi": "35 litr", "Mato": "Oksford 600D suv o'tkazmas", "Tasmalari": "Yelkama yumshoq yostiqchali"}),
            json.dumps({"Rang": ["Qora", "To'q ko'k", "Havorang"]}),
            1, 0
        ),
        (
            "Elektron qo'l kuchi o'lchagich (Dinamometr) Digital Grip",
            "sport-dinamometr-digital-grip",
            6, 1, 95000, 130000, 27, 40, 4.78, 51, 210, "CHEGIRMA",
            "finger-print", "linear-gradient(135deg, #2563eb, #1d4ed8)",
            "Qo'l panjasi kuchini 90 kg gacha yuqori aniqlikda o'lchovchi, yosh va jins bo'yicha baholovchi qurilma.",
            json.dumps({"Maksimal og'irlik": "90 kg / 198 lb", "Xotira": "19 ta foydalanuvchi", "Displey": "Aniq raqamli LCD"}),
            json.dumps({"Rang": ["Moviy", "Kulrang"]}),
            0, 0
        ),

        # 7. Oziq-ovqat (49-56)
        (
            "Samarqand pista va bodomli qandolat holvasi 500g",
            "oziq-ovqat-samarqand-holvasi-500g",
            7, 3, 45000, 60000, 25, 80, 4.96, 210, 1100, "XIT SAVDO",
            "nutrition", "linear-gradient(135deg, #d97706, #b45309)",
            "Qadimiy retsept bo'yicha tayyorlangan, erib ketuvchi tabiiy qaymoqli va mo'l pista yong'oqli holva.",
            json.dumps({"Og'irligi": "500 gramm", "Tarkibi": "Sut qaymog'i, shakar, bodom, pista, vanilin", "Muddati": "6 oy"}),
            json.dumps({"Turi": ["Pistali qaymoq", "Shokoladli bodom"]}),
            1, 1
        ),
        (
            "Tabiiy tog' asal to'plami tog' giyohlari bilan 1 kg",
            "oziq-ovqat-tabiiy-tog-asal-1kg",
            7, 3, 110000, 150000, 27, 35, 4.97, 185, 780, "TAVSIYA",
            "flower", "linear-gradient(135deg, #f59e0b, #d97706)",
            "Zomin va Bo'stonliq tog'laridan yig'ilgan shifobaxsh, hech qanday shakar qo'shilmagan toza asal.",
            json.dumps({"Og'irligi": "1000 g (1 kg)", "Kelib chiqishi": "O'zbekiston, tog'li hududlar", "Turi": "Tog' o'tlari polifloral"}),
            json.dumps({"Hajmi": ["1 kg shisha banka", "0.5 kg banka"]}),
            0, 1
        ),
        (
            "Premium arab donli kofe 'Espresso Arabica Crema' 1000g",
            "oziq-ovqat-kofe-donli-arabica-1000g",
            7, 3, 180000, 240000, 25, 30, 4.89, 92, 430, "CHEGIRMA",
            "cafe", "linear-gradient(135deg, #78350f, #451a03)",
            "O'rtacha qovurilgan Kolumbiya va Braziliya 100% Arabika donalari. Mayin nordonlik va shokolad ta'mi.",
            json.dumps({"Tarkibi": "100% Arabica", "Qovurish darajasi": "O'rtacha (Medium Roast)", "Vazni": "1000 gramm", "Vakuum qadoq": "Klapanli paket"}),
            json.dumps({"Turi": ["Butun donalar", "Maydalangan espresso uchun"]}),
            1, 0
        ),
        (
            "Zaytun moyi Extra Virgin birinchi sovuq siqim 1 litr",
            "oziq-ovqat-zaytun-moyi-extra-virgin-1l",
            7, 3, 135000, 180000, 25, 45, 4.91, 114, 520, "XIT SAVDO",
            "water", "linear-gradient(135deg, #65a30d, #4d7c0f)",
            "Ispaniyaning eng saralangan zaytun mevalaridan tayyorlangan kislotaligi 0.3% dan past bo'lgan oliy moy.",
            json.dumps({"Hajmi": "1 Litr", "Siqim turi": "Birinchi sovuq siqish (Extra Virgin)", "Idish": "To'q rangli shisha"}),
            json.dumps({"Hajmi": ["1 Litr", "500 ml"]}),
            0, 0
        ),
        (
            "Yong'oqlar va quruq mevalar miksi 'Vitamin Mix' 700g",
            "oziq-ovqat-yong'oq-quruq-meva-miksi",
            7, 3, 92000, 125000, 26, 50, 4.88, 140, 670, "CHEGIRMA",
            "nutrition", "linear-gradient(135deg, #b45309, #78350f)",
            "Bodom, keshpyu, yong'oq mag'zi, mayiz, quritilgan anjir va klyukva mevalaridan tashkil topgan boy to'plam.",
            json.dumps({"Vazni": "700 gramm", "Tarkibi": "6 turdagi yong'oq va quruq meva", "Qadoqlash": "Zip-lock paket"}),
            json.dumps({"Variant": ["Klassik to'plam 700g", "Qovurilgan yong'oqlar 500g"]}),
            1, 0
        ),
        (
            "Oliy navli Samarqand qizil guruchi 'Devzira' 2 kg",
            "oziq-ovqat-guruch-devzira-2kg",
            7, 3, 70000, 95000, 26, 40, 4.95, 160, 890, "XIT SAVDO",
            "restaurant", "linear-gradient(135deg, #dc2626, #b91c1c)",
            "Haqiqiy Farg'ona va Samarqand oshi uchun saralangan, suvni va yog'ni mukammal tortuvchi guruch.",
            json.dumps({"Og'irligi": "2 kg", "Navi": "Devzira Oliy nav", "Tozalik darajasi": "Qo'lda saralangan"}),
            json.dumps({"Vazn": ["2 kg", "5 kg xalta"]}),
            0, 1
        ),
        (
            "Shveysariya sutli shokoladi to'plami 'Alpen Gold Trio' 5x100g",
            "oziq-ovqat-shveysariya-shokolad-toplami",
            7, 3, 85000, 115000, 26, 60, 4.87, 83, 390, "YANGI",
            "gift", "linear-gradient(135deg, #9333ea, #7e22ce)",
            "Yong'oqli, karamelli va mayin quyuq sutli haqiqiy shokolad plitkalari to'plami.",
            json.dumps({"Umumiy og'irlik": "500 gramm (5 ta plitka)", "Kakao miqdori": "Kamida 32%", "Sertifikat": "Halol standart"}),
            json.dumps({"Turi": ["Sutli miks", "Qora achchiq miks"]}),
            1, 0
        ),
        (
            "Yashil choy 'Zarafshon durdonasi' bargli ko'k choy 250g",
            "oziq-ovqat-yashil-choy-zarafshon",
            7, 3, 38000, 52000, 27, 90, 4.91, 120, 610, "CHEGIRMA",
            "leaf", "linear-gradient(135deg, #15803d, #166534)",
            "Yirik bargli, yorqin tetiklashtiruvchi iforga ega bo'lgan 95-raqamli an'anaviy o'zbek ko'k choyi.",
            json.dumps({"Og'irligi": "250 gramm", "Turi": "Yirik bargli ko'k choy No 95", "Qadoq": "Metall naycha banka"}),
            json.dumps({"Turi": ["An'anaviy ko'k choy", "Yasmin guli qo'shilgan"]}),
            0, 0
        ),

        # 8. Kitoblar (57-64)
        (
            "Atom odatlari - Jeyms Klir (O'zbek tilida qattiq muqova)",
            "kitoblar-atom-odatlari-jeyms-klir",
            8, 1, 65000, 85000, 24, 75, 4.98, 380, 1950, "XIT SAVDO",
            "book", "linear-gradient(135deg, #f59e0b, #d97706)",
            "Mayda o'zgarishlar qanday qilib ulkan natijalarga olib kelishini ilmiy va amaliy tushuntirib beruvchi jahon bestselleri.",
            json.dumps({"Muallif": "Jeyms Klir", "Muqova": "Qattiq", "Sahifalar soni": "320 bet", "Tili": "O'zbekcha (Lotin)", "Yili": "2024"}),
            json.dumps({"Muqova": ["Qattiq muqova", "Yumshoq muqova (-15 000)"]}),
            1, 1
        ),
        (
            "Stiv Jobs - Uolter Ayzekson tarjimai holi",
            "kitoblar-stiv-jobs-tarjimai-hol",
            8, 1, 85000, 110000, 23, 40, 4.94, 142, 630, "TAVSIYA",
            "bulb", "linear-gradient(135deg, #1e293b, #0f172a)",
            "Apple kompaniyasi asoschisining hayoti, yutuqlari va murosasiz xarakteri haqidagi yagona rasmiy biografiya.",
            json.dumps({"Muallif": "Uolter Ayzekson", "Muqova": "Qattiq oltin zarli", "Sahifalar soni": "640 bet", "Nashriyot": "Yangi Asr Avlodi"}),
            json.dumps({"Muqova": ["Qattiq muqova"]}),
            0, 1
        ),
        (
            "Boy ota, kambag'al ota - Robert Kiyosaki",
            "kitoblar-boy-ota-kambag'al-ota",
            8, 1, 55000, 75000, 27, 85, 4.91, 260, 1420, "CHEGIRMA",
            "cash", "linear-gradient(135deg, #854d0e, #713f12)",
            "Moliyaviy savodxonlik, passiv daromad va investitsiyalar olamiga yo'l ko'rsatuvchi eng mashhur kitob.",
            json.dumps({"Muallif": "Robert Kiyosaki", "Sahifalar soni": "288 bet", "Muqova": "Yumshoq laq", "Tili": "O'zbekcha"}),
            json.dumps({"Format": ["Yumshoq muqova", "Qattiq sovg'abop"]}),
            1, 0
        ),
        (
            "Diqqat: Chalg'ituvchi dunyoda muvaffaqiyat sirlari - Kel Nyuport",
            "kitoblar-diqqat-kel-nyuport",
            8, 1, 60000, 80000, 25, 45, 4.88, 98, 410, "YANGI",
            "eye", "linear-gradient(135deg, #2563eb, #1d4ed8)",
            "Chuqur ishlash qobiliyati va internet shovqinidan xoli holda mahsuldorlikni 10 barobarga oshirish usullari.",
            json.dumps({"Muallif": "Kel Nyuport", "Sahifalar soni": "272 bet", "Mavzu": "Shaxsiy rivojlanish, diqqat"}),
            json.dumps({"Muqova": ["Qattiq muqova"]}),
            0, 0
        ),
        (
            "O'tkan kunlar - Abdulla Qodiriy (Oltin meros nashri)",
            "kitoblar-otkan-kunlar-abdulla-qodiriy",
            8, 1, 50000, 70000, 29, 60, 4.99, 410, 2100, "XIT SAVDO",
            "library", "linear-gradient(135deg, #0f766e, #115e59)",
            "O'zbek adabiyotining durdona asari bo'lmish ilk romani, Otabek va Kumushbibining mangu sevgisi.",
            json.dumps({"Muallif": "Abdulla Qodiriy", "Sahifalar": "384 bet", "Format": "A5 qattiq muqova, sovg'abop bezak"}),
            json.dumps({"Muqova": ["Qattiq charmli", "Standart qattiq"]}),
            1, 0
        ),
        (
            "Dasturlash asoslari: Python tilida mukammal qo'llanma",
            "kitoblar-python-dasturlash-asoslari",
            8, 1, 95000, 130000, 27, 30, 4.90, 85, 360, "TAVSIYA",
            "code-slash", "linear-gradient(135deg, #3b82f6, #1d4ed8)",
            "Boshlovchilar va talabalar uchun amaliy misollar, mashqlar va real loyihalar bilan to'ldirilgan darslik.",
            json.dumps({"Muallif": "Anvar Narzullayev", "Sahifalar": "480 bet", "QR kodlar": "Video darslarga havolalar mavjud"}),
            json.dumps({"Muqova": ["Qattiq muqova"]}),
            0, 1
        ),
        (
            "Vaqtni boshqarish san'ati: Pomodoro va Taym-menejment",
            "kitoblar-vaqtni-boshqarish-sanati",
            8, 1, 48000, 65000, 26, 50, 4.82, 64, 280, "CHEGIRMA",
            "time", "linear-gradient(135deg, #dc2626, #991b1b)",
            "Kunni to'g'ri rejalashtirish, charchoqni yengish va rejalashtirilgan maqsadlarga 100% erishish tizimi.",
            json.dumps({"Sahifalar soni": "208 bet", "Muqova": "Yumshoq", "Tili": "O'zbek tili"}),
            json.dumps({"Muqova": ["Yumshoq muqova"]}),
            1, 0
        ),
        (
            "Bolalar uchun qiziqarli ensiklopediya: Koinot va Sayyoralar",
            "kitoblar-koinot-va-sayyoralar-ensiklopediya",
            8, 1, 78000, 105000, 26, 35, 4.96, 112, 490, "XIT SAVDO",
            "planet", "linear-gradient(135deg, #4338ca, #3730a3)",
            "Yorqin rangli illyustratsiyalar, yulduzlar, galaktikalar va qora tuynuklar haqida hayratlanarli ma'lumotlar.",
            json.dumps({"Format": "Katta A4 format", "Sahifalar": "160 bet to'liq rangli bo'r qog'oz", "Muqova": "Qattiq yaltiroq"}),
            json.dumps({"Format": ["Katta format (A4)"]}),
            0, 0
        )
    ]

    cursor.executemany("""
    INSERT INTO products (
        title, slug, category_id, seller_id, price, old_price, discount_percent,
        stock, rating, reviews_count, sales_count, badge, icon_svg, gradient_theme,
        description, specifications, variants, is_flash_sale, is_featured
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, raw_products)

    sample_reviews = [
        (1, "Jasurbek Aliyev", 5, "Mahsulot juda ajoyib! Kecha buyurtma qilgandim, bugun ertalab yetkazib berishdi. Sifati 100% original, raxmat BozorUz!"),
        (1, "Malika Yusupova", 5, "Muddatli to'lovga oldim, 5 daqiqada tasdiqlandi. Rangi nihoyatda chiroyli ekan, kamerasi gap bo'lishi mumkin emas."),
        (3, "Bobur Mirzaev", 5, "Shovqin bostirishi zo'r ishlayapti, metrosda ham hech narsa eshitilmaydi. Narxiga 2 barobar arziydi."),
        (9, "Shaxzod Bek", 4, "Ko'ylak matosi toza paxta, dazmoli oson ekan. O'lchami to'g'ri keldi, tavsiya qilaman."),
        (17, "Gulchehra opa", 5, "Uyimizni shunaqangi toza qilyaptiki, o'zim hayronman. Gilamdagi mayda changlargacha qoldirmay tortadi!"),
        (25, "Dilnoza Rahimova", 5, "Dyson apparatidan hech qolishmaydi, sochlarimni yarim soatda salon darajasida shakllantirdim."),
        (41, "Otabek Qodirov", 5, "Kvartiramizga juda mos tushdi, trenajyor yig'ilganda umuman joy olmaydi. Dvigateli ancha sokin ishlar ekan."),
        (57, "Farrux Zokirov", 5, "Har bir inson o'qishi shart bo'lgan kitob. Hayotimdagi odatlarni butunlay o'zgartirdi. Yetkazish juda tez bo'ldi.")
    ]
    cursor.executemany("""
    INSERT INTO reviews (product_id, user_name, rating, comment)
    VALUES (?, ?, ?, ?)
    """, sample_reviews)

    sample_order_items = json.dumps([
        {"id": 1, "title": "Smartfon UltraPro 15 Max 256GB Titanium", "price": 14200000, "qty": 1, "variant": "Tabiiy titan", "icon": "phone"},
        {"id": 3, "title": "Simsiz quloqchin AirBeats SoundPro ANC", "price": 480000, "qty": 1, "variant": "Mat qora", "icon": "headset"}
    ], ensure_ascii=False)

    cursor.execute("""
    INSERT INTO orders (
        order_number, user_id, customer_name, phone, address,
        payment_method, total_price, discount_amount, final_price,
        promo_code, status, items_json, installment_months, monthly_payment
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "BUZ-849201", 2, "Davron Karimov", "+998935557788", "Samarqand sh., Registon ko'chasi 21-uy",
        "Click / Payme (Karta)", 14680000, 100000, 14580000,
        "BOZORUZ10", "yetkazildi", sample_order_items, 0, 0
    ))

    conn.commit()
    conn.close()

def get_products(filters: dict = None) -> list:
    conn = get_db()
    cursor = conn.cursor()

    sql = """
    SELECT p.*, c.name as category_name, c.slug as category_slug, s.name as seller_name
    FROM products p
    JOIN categories c ON p.category_id = c.id
    JOIN sellers s ON p.seller_id = s.id
    WHERE 1=1
    """
    params = []

    if filters:
        if filters.get('category'):
            sql += " AND c.slug = ?"
            params.append(filters['category'])

        if filters.get('category_id'):
            sql += " AND p.category_id = ?"
            params.append(filters['category_id'])

        if filters.get('seller_id'):
            sql += " AND p.seller_id = ?"
            params.append(filters['seller_id'])

        if filters.get('min_price'):
            try:
                min_p = int(filters['min_price'])
                sql += " AND p.price >= ?"
                params.append(min_p)
            except (ValueError, TypeError):
                pass

        if filters.get('max_price'):
            try:
                max_p = int(filters['max_price'])
                sql += " AND p.price <= ?"
                params.append(max_p)
            except (ValueError, TypeError):
                pass

        if filters.get('rating'):
            try:
                min_r = float(filters['rating'])
                sql += " AND p.rating >= ?"
                params.append(min_r)
            except (ValueError, TypeError):
                pass

        if filters.get('has_discount'):
            sql += " AND p.discount_percent > 0"

        if filters.get('is_flash_sale'):
            sql += " AND p.is_flash_sale = 1"

        if filters.get('is_featured'):
            sql += " AND p.is_featured = 1"

        if filters.get('search'):
            term = f"%{filters['search'].strip()}%"
            sql += " AND (p.title LIKE ? OR p.description LIKE ? OR c.name LIKE ?)"
            params.extend([term, term, term])

        # Saralash
        sort = filters.get('sort', 'popular')
        if sort == 'cheap':
            sql += " ORDER BY p.price ASC"
        elif sort == 'expensive':
            sql += " ORDER BY p.price DESC"
        elif sort == 'new':
            sql += " ORDER BY p.id DESC"
        elif sort == 'discount':
            sql += " ORDER BY p.discount_percent DESC"
        elif sort == 'rating':
            sql += " ORDER BY p.rating DESC"
        else: # popular
            sql += " ORDER BY p.sales_count DESC, p.rating DESC"

        if filters.get('limit'):
            sql += " LIMIT ?"
            params.append(int(filters['limit']))
            if filters.get('offset'):
                sql += " OFFSET ?"
                params.append(int(filters['offset']))

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_product_by_id(p_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT p.*, c.name as category_name, c.slug as category_slug,
           s.name as seller_name, s.rating as seller_rating, s.reviews_count as seller_reviews
    FROM products p
    JOIN categories c ON p.category_id = c.id
    JOIN sellers s ON p.seller_id = s.id
    WHERE p.id = ?
    """, (p_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    product = dict(row)

    try:
        product['specs_dict'] = json.loads(product['specifications']) if product['specifications'] else {}
    except Exception:
        product['specs_dict'] = {}

    try:
        product['variants_dict'] = json.loads(product['variants']) if product['variants'] else {}
    except Exception:
        product['variants_dict'] = {}

    cursor.execute("SELECT * FROM reviews WHERE product_id = ? ORDER BY id DESC", (p_id,))
    product['reviews'] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return product

def get_user_by_phone(phone: str) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def apply_promo_code(code: str, total_sum: int) -> dict:
    if not code:
        return {"valid": False, "discount": 0, "message": "Promokod kiritilmadi"}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promo_codes WHERE code = ? AND is_active = 1", (code.strip().upper(),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"valid": False, "discount": 0, "message": "Yaroqsiz yoki eskirgan promokod"}

    promo = dict(row)
    if total_sum < promo['min_amount']:
        return {
            "valid": False,
            "discount": 0,
            "message": f"Ushbu promokod faqat {promo['min_amount']:,} so'mdan ortiq xaridlarda ishlaydi"
        }

    raw_disc = int(total_sum * (promo['discount_percent'] / 100.0))
    discount = min(raw_disc, promo['max_discount'])

    return {
        "valid": True,
        "discount": discount,
        "percent": promo['discount_percent'],
        "code": promo['code'],
        "message": f"Tabriklaymiz! {promo['discount_percent']}% chegirma qo'llandi (-{discount:,} so'm)"
    }

def create_order(user_id: int, items: list, shipping_data: dict, promo_code: str = None) -> int:
    conn = get_db()
    cursor = conn.cursor()

    total_price = 0
    items_to_save = []

    for item in items:
        p_id = item.get('id')
        qty = item.get('quantity', 1)
        cursor.execute("SELECT id, title, price, icon_svg FROM products WHERE id = ?", (p_id,))
        p = cursor.fetchone()
        if p:
            subtotal = p['price'] * qty
            total_price += subtotal
            items_to_save.append({
                "id": p['id'],
                "title": p['title'],
                "price": p['price'],
                "quantity": qty,
                "variant": item.get('variant', 'Standart'),
                "subtotal": subtotal,
                "icon": p['icon_svg']
            })
            cursor.execute("UPDATE products SET sales_count = sales_count + ?, stock = MAX(0, stock - ?) WHERE id = ?", (qty, qty, p_id))

    discount_amount = 0
    if promo_code:
        promo_res = apply_promo_code(promo_code, total_price)
        if promo_res['valid']:
            discount_amount = promo_res['discount']

    final_price = max(0, total_price - discount_amount)

    order_num = f"BUZ-{int(datetime.now().timestamp()) % 1000000:06d}"
    installment_months = int(shipping_data.get('installment_months', 0))
    monthly_payment = 0
    if installment_months in [3, 6, 12] and installment_months > 0:
        monthly_payment = int(final_price / installment_months)

    cursor.execute("""
    INSERT INTO orders (
        order_number, user_id, customer_name, phone, address,
        payment_method, total_price, discount_amount, final_price,
        promo_code, status, items_json, installment_months, monthly_payment
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_num,
        user_id,
        shipping_data.get('name', 'Noma\'lum xaridor'),
        shipping_data.get('phone', ''),
        shipping_data.get('address', 'Olib ketish punkti'),
        shipping_data.get('payment_method', 'Naqd pul / Qabulda'),
        total_price,
        discount_amount,
        final_price,
        promo_code if discount_amount > 0 else None,
        'yangi',
        json.dumps(items_to_save, ensure_ascii=False),
        installment_months,
        monthly_payment
    ))

    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_dashboard_analytics() -> dict:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(final_price), 0) FROM orders WHERE status != 'bekor'")
    total_revenue = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
    total_users = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COALESCE(SUM(final_price), 0) FROM orders
    WHERE DATE(created_at) = DATE('now') AND status != 'bekor'
    """)
    today_revenue = cursor.fetchone()[0]

    cursor.execute("""
    SELECT p.id, p.title, p.stock, p.price, c.name as category_name
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.stock <= 5
    ORDER BY p.stock ASC
    LIMIT 6
    """)
    low_stock_products = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
    SELECT p.id, p.title, p.sales_count, p.price, p.rating, p.icon_svg
    FROM products p
    ORDER BY p.sales_count DESC
    LIMIT 5
    """)
    top_selling = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
    SELECT DATE(created_at) as order_date, COALESCE(SUM(final_price), 0) as day_total, COUNT(*) as count
    FROM orders
    WHERE created_at >= DATE('now', '-6 days')
    GROUP BY DATE(created_at)
    ORDER BY order_date ASC
    """)
    weekly_sales = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
    SELECT id, order_number, customer_name, phone, final_price, status, created_at, payment_method
    FROM orders
    ORDER BY id DESC
    LIMIT 8
    """)
    recent_orders = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_products": total_products,
        "total_users": total_users,
        "today_revenue": today_revenue,
        "low_stock_products": low_stock_products,
        "top_selling": top_selling,
        "weekly_sales": weekly_sales,
        "recent_orders": recent_orders
    }

init_db()
seed_initial_data()