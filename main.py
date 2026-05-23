import os
import hashlib
import sqlite3
import json
import uuid
from datetime import datetime
from functools import wraps

import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fakka-shop-secret-key-2026")

# ======================== Config ========================
CLIENT_ID = "cash-app"
CLIENT_SECRET = "b86e30a8-ae29-467a-a71f-65c73f2ff5e3"
DEVICE_ID = "b26ba335813fad21"
MERCHANT_CODE = "81841829"
USER_AGENT = "okhttp/4.12.0"
DEVICE_MODEL = "Samsung SM-A165F"
APP_VERSION = "2025.11.1"
APP_BUILD = "1063"

FAKKA_PRODUCTS = [
    {"id": "Fakka_2.5_Unite", "name": "45 وحدة لمدة يوم", "price": 2.5},
    {"id": "Fakka_4.25_Unite", "name": "190 وحدة لمدة يوم", "price": 4.25},
    {"id": "Fakka_5_Unite", "name": "225 وحدة لمدة يوم", "price": 5.0},
    {"id": "Fakka_6_Unite", "name": "225 وحدة لمدة يوم", "price": 6.0},
    {"id": "Fakka_7_Unite", "name": "400 وحدة لمدة 4 أيام", "price": 7.0},
    {"id": "Fakka_9_Unite", "name": "400 وحدة لمدة 4 أيام", "price": 9.0},
    {"id": "Fakka_10_Unite", "name": "450 وحدة لمدة 7 أيام", "price": 10.0},
    {"id": "Fakka_10.5_Unite", "name": "450 وحدة لمدة 7 أيام", "price": 10.5},
    {"id": "Fakka_11.5_Unite", "name": "450 وحدة لمدة 7 أيام", "price": 11.5},
    {"id": "Fakka_12_Unite", "name": "625 وحدة لمدة 7 أيام", "price": 12.0},
    {"id": "Fakka_12.5_Unite", "name": "625 وحدة لمدة 7 أيام", "price": 12.5},
    {"id": "Fakka_13_Unite", "name": "650 وحدة لمدة 10 أيام", "price": 13.0},
    {"id": "Fakka_13.5_Unite", "name": "650 وحدة لمدة 10 أيام", "price": 13.5},
    {"id": "Fakka_15_Unite", "name": "650 وحدة لمدة 10 أيام", "price": 15.0},
    {"id": "Fakka_15.5_Unite", "name": "750 وحدة لمدة 10 أيام", "price": 15.5},
    {"id": "Fakka_16.5_Unite", "name": "750 وحدة لمدة 10 أيام", "price": 16.5},
    {"id": "Fakka_17.5_Unite", "name": "650 وحدة لمدة 10 أيام", "price": 17.5},
    {"id": "Fakka_20_Unite", "name": "750 وحدة لمدة 10 أيام", "price": 20.0},
    {"id": "Fakka_26_Unite", "name": "750 وحدة لمدة 10 أيام", "price": 26.0},
]

# ======================== Database ========================
DB_PATH = os.environ.get("DB_PATH", "fakka_shop.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        stars INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        receiver TEXT NOT NULL,
        product_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        product_price REAL NOT NULL,
        status TEXT NOT NULL,
        details TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS star_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        stars INTEGER NOT NULL,
        amount REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )''')

    # Default settings
    c.execute("SELECT COUNT(*) FROM settings WHERE key='star_price'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO settings VALUES ('star_price', '2.5')")

    # Default admin
    c.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, stars, is_admin) VALUES (?, ?, ?, ?)",
                  ('admin', sha256_hash('admin123'), 0, 1))
        c.execute("INSERT INTO users (username, password, stars, is_admin) VALUES (?, ?, ?, ?)",
                  ('test', sha256_hash('admin123'), 50, 0))

    conn.commit()
    conn.close()


def sha256_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


# Initialize DB on import for WSGI servers like gunicorn
init_db()

# ======================== Auth ========================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
        conn.close()
        if not user or not user['is_admin']:
            return jsonify({'error': 'صلاحيات الأدمن مطلوبة'}), 403
        return f(*args, **kwargs)
    return decorated


# ======================== Vodafone API ========================
def get_common_headers():
    return {
        "User-Agent": USER_AGENT,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "x-agent-operatingsystem": "16",
        "clientId": "AnaVodafoneAndroid",
        "Accept-Language": "ar",
        "x-agent-device": DEVICE_MODEL,
        "x-agent-version": APP_VERSION,
        "x-agent-build": APP_BUILD,
        "digitalId": "",
        "device-id": DEVICE_ID,
    }


def get_seamless_and_msisdn():
    """Step 1: Get seamless token and MSISDN"""
    try:
        headers = get_common_headers()
        headers["If-Modified-Since"] = "Thu, 02 Apr 2026 09:09:07 GMT"

        url = f"http://mobile.vodafone.com.eg/checkSeamless/realms/vf-realm/protocol/openid-connect/auth?client_id={CLIENT_ID}"
        resp = requests.get(url, headers=headers, timeout=30, allow_redirects=True)

        if resp.status_code != 200:
            return None, f"فشل الاتصال: HTTP {resp.status_code}"

        data = resp.json()
        msisdn = data.get("msisdn", "")
        if not msisdn:
            return None, "لم يتم التعرف على الرقم - تأكد أنك على شبكة فودافون"

        seamless_token = data.get("seamlessToken", "")
        if msisdn.startswith("1"):
            msisdn = "0" + msisdn

        return {"seamlessToken": seamless_token, "msisdn": msisdn}, None
    except Exception as e:
        return None, f"خطأ في الاتصال: {str(e)}"


def get_access_token(seamless_token):
    """Step 2: Get access token via Keycloak"""
    try:
        headers = get_common_headers()
        headers.update({
            "Accept": "application/json, text/plain, */*",
            "silentLogin": "true",
            "CRP": "false",
            "seamlessToken": seamless_token,
            "firstTimeLogin": "true",
            "Content-Type": "application/x-www-form-urlencoded",
        })

        payload = f"grant_type=password&client_secret={CLIENT_SECRET}&client_id={CLIENT_ID}"
        url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        resp = requests.post(url, headers=headers, data=payload, timeout=30, allow_redirects=True)

        if resp.status_code != 200:
            return None, f"فشل المصادقة: HTTP {resp.status_code}"

        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            return None, "لم يتم الحصول على access token"

        return access_token, None
    except Exception as e:
        return None, f"خطأ في المصادقة: {str(e)}"


def purchase_product(product_id, msisdn, receiver, pin, access_token):
    """Step 3: Purchase fakka product"""
    try:
        headers = get_common_headers()
        headers.update({
            "Accept": "application/json",
            "api-host": "ProductOrderingManagement",
            "useCase": "CashFakkaAndMared",
            "X-Request-ID": str(uuid.uuid4()),
            "api-version": "v2",
            "msisdn": msisdn,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        })

        payload = {
            "channel": {"name": "MobileApp"},
            "orderItem": [{
                "action": "insert",
                "id": product_id,
                "product": {
                    "characteristic": [
                        {"name": "PaymentMethod", "value": "VFCash"},
                        {"name": "USE_EMONEY", "value": "False"},
                        {"name": "MerchantCode", "value": MERCHANT_CODE},
                    ],
                    "id": product_id,
                    "relatedParty": [
                        {"id": msisdn, "name": "MSISDN", "role": "Subscriber"},
                        {"id": receiver, "name": "Receiver", "role": "Receiver"},
                    ],
                },
                "@type": product_id,
                "eCode": 0,
            }],
            "relatedParty": [{"id": pin, "name": "pin", "role": "Requestor"}],
            "@type": "CashFakkaAndMared",
        }

        url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
        resp = requests.post(url, headers=headers, json=payload, timeout=60, allow_redirects=True)

        if resp.status_code in [200, 201, 202, 204]:
            try:
                r = resp.json()
                code = r.get("code", "")
                if code in ["", "0000", "0", "200"]:
                    return True, "تم الشحن بنجاح"
                else:
                    return False, r.get("message", f"كود: {code}")
            except:
                return True, "تم الشحن بنجاح"
        else:
            try:
                err = resp.json()
                return False, err.get("message", f"HTTP {resp.status_code}")
            except:
                return False, f"HTTP {resp.status_code} - تأكد من الرقم السري"
    except Exception as e:
        return False, f"خطأ في الشحن: {str(e)}"


# ======================== Routes ========================
@app.route('/')
def index():
    if 'user_id' in session:
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
        conn.close()
        if user and user['is_admin']:
            return render_template('index.html', user=dict(user), is_admin=True)
        return render_template('index.html', user=dict(user), is_admin=False)
    return render_template('index.html', user=None, is_admin=False)


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'أدخل اسم المستخدم والرقم السري'}), 400

    hashed = sha256_hash(password)
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                        (username, hashed)).fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'اسم المستخدم أو الرقم السري غير صحيح'}), 401

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['is_admin'] = bool(user['is_admin'])

    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'stars': user['stars'],
            'is_admin': bool(user['is_admin'])
        }
    })


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/me', methods=['GET'])
@login_required
def api_me():
    conn = get_db()
    user = conn.execute("SELECT id, username, stars, is_admin FROM users WHERE id=?",
                        (session['user_id'],)).fetchone()
    conn.close()
    if not user:
        session.clear()
        return jsonify({'error': 'المستخدم غير موجود'}), 404
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'stars': user['stars'],
        'is_admin': bool(user['is_admin'])
    })


@app.route('/api/products', methods=['GET'])
def api_products():
    return jsonify(FAKKA_PRODUCTS)


@app.route('/api/charge', methods=['POST'])
@login_required
def api_charge():
    data = request.get_json()
    product_id = data.get('product_id', '').strip()
    receiver = data.get('receiver', '').strip()
    pin = data.get('pin', '').strip()

    # Validation
    if not receiver or len(receiver) != 11 or not receiver.startswith('01'):
        return jsonify({'error': 'أدخل رقم صحيح 11 رقم يبدأ بـ 01'}), 400
    if not pin or len(pin) != 6 or not pin.isdigit():
        return jsonify({'error': 'أدخل الرقم السري 6 أرقام'}), 400

    # Check product
    product = None
    for p in FAKKA_PRODUCTS:
        if p['id'] == product_id:
            product = p
            break
    if not product:
        return jsonify({'error': 'منتج غير صحيح'}), 400

    # Check stars
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if not user or user['stars'] < 1:
        conn.close()
        return jsonify({'error': 'رصيد نجوم غير كافٍ - تواصل مع الأدمن'}), 400

    # Deduct star first
    conn.execute("UPDATE users SET stars = stars - 1 WHERE id=? AND stars > 0", (session['user_id'],))
    conn.commit()

    # Step 1: Seamless
    seamless_result, err = get_seamless_and_msisdn()
    if err:
        # Refund star on failure
        conn.execute("UPDATE users SET stars = stars + 1 WHERE id=?", (session['user_id'],))
        conn.execute("INSERT INTO transactions (user_id, receiver, product_id, product_name, product_price, status, details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (session['user_id'], receiver, product_id, product['name'], product['price'], 'فشل', err, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'error': err}), 400

    # Step 2: Access Token
    access_token, err = get_access_token(seamless_result['seamlessToken'])
    if err:
        conn.execute("UPDATE users SET stars = stars + 1 WHERE id=?", (session['user_id'],))
        conn.execute("INSERT INTO transactions (user_id, receiver, product_id, product_name, product_price, status, details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (session['user_id'], receiver, product_id, product['name'], product['price'], 'فشل', err, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'error': err}), 400

    # Step 3: Purchase
    success, message = purchase_product(product_id, seamless_result['msisdn'], receiver, pin, access_token)

    status = 'نجاح' if success else 'فشل'
    if not success:
        # Refund star on failure
        conn.execute("UPDATE users SET stars = stars + 1 WHERE id=?", (session['user_id'],))

    conn.execute("INSERT INTO transactions (user_id, receiver, product_id, product_name, product_price, status, details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (session['user_id'], receiver, product_id, product['name'], product['price'], status, message, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 400


@app.route('/api/transactions', methods=['GET'])
@login_required
def api_transactions():
    conn = get_db()
    if session.get('is_admin'):
        transactions = conn.execute(
            "SELECT t.*, u.username FROM transactions t JOIN users u ON t.user_id=u.id ORDER BY t.created_at DESC LIMIT 50"
        ).fetchall()
    else:
        transactions = conn.execute(
            "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 30",
            (session['user_id'],)
        ).fetchall()
    conn.close()
    return jsonify([dict(t) for t in transactions])


# ======================== Admin APIs ========================
@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def api_admin_stats():
    conn = get_db()
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    trans_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    star_price = conn.execute("SELECT value FROM settings WHERE key='star_price'").fetchone()[0]
    conn.close()
    return jsonify({
        'users': user_count,
        'transactions': trans_count,
        'star_price': float(star_price)
    })


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def api_admin_users():
    conn = get_db()
    users = conn.execute("SELECT id, username, stars, is_admin FROM users ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])


@app.route('/api/admin/add_user', methods=['POST'])
@admin_required
def api_admin_add_user():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'أدخل اسم المستخدم والرقم السري'}), 400
    if len(username) < 3:
        return jsonify({'error': 'اسم المستخدم لازم 3 حروف على الأقل'}), 400

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'اسم المستخدم موجود مسبقاً'}), 400

    conn.execute("INSERT INTO users (username, password, stars, is_admin) VALUES (?, ?, 0, 0)",
                 (username, sha256_hash(password)))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'تم إضافة المستخدم {username}'})


@app.route('/api/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def api_admin_delete_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'المستخدم غير موجود'}), 404
    if user['is_admin']:
        conn.close()
        return jsonify({'error': 'لا يمكن حذف الأدمن'}), 400

    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/admin/add_stars', methods=['POST'])
@admin_required
def api_admin_add_stars():
    data = request.get_json()
    user_id = data.get('user_id')
    stars = data.get('stars', 0)

    if not user_id or stars < 40:
        return jsonify({'error': f'الحد الأدنى {40} نجمة'}), 400

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'المستخدم غير موجود'}), 404

    star_price = float(conn.execute("SELECT value FROM settings WHERE key='star_price'").fetchone()[0])
    amount = stars * star_price

    conn.execute("UPDATE users SET stars = stars + ? WHERE id=?", (stars, user_id))
    conn.execute("INSERT INTO star_purchases (user_id, stars, amount, created_at) VALUES (?, ?, ?, ?)",
                 (user_id, stars, amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'تم إضافة {stars} نجمة بقيمة {amount} جنيه'})


@app.route('/api/admin/edit_stars', methods=['POST'])
@admin_required
def api_admin_edit_stars():
    data = request.get_json()
    user_id = data.get('user_id')
    new_stars = data.get('stars')

    if user_id is None or new_stars is None or new_stars < 0:
        return jsonify({'error': 'قيمة غير صحيحة'}), 400

    conn = get_db()
    conn.execute("UPDATE users SET stars=? WHERE id=?", (new_stars, user_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'تم تعديل الرصيد إلى {new_stars} نجمة'})


@app.route('/api/admin/star_price', methods=['GET', 'POST'])
@admin_required
def api_admin_star_price():
    conn = get_db()
    if request.method == 'GET':
        price = conn.execute("SELECT value FROM settings WHERE key='star_price'").fetchone()[0]
        conn.close()
        return jsonify({'star_price': float(price)})

    data = request.get_json()
    new_price = data.get('star_price')
    if not new_price or new_price <= 0:
        conn.close()
        return jsonify({'error': 'سعر غير صحيح'}), 400

    conn.execute("UPDATE settings SET value=? WHERE key='star_price'", (str(new_price),))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'تم تغيير السعر إلى {new_price} جنيه'})


@app.route('/api/admin/star_purchases', methods=['GET'])
@admin_required
def api_admin_star_purchases():
    conn = get_db()
    purchases = conn.execute(
        "SELECT s.*, u.username FROM star_purchases s JOIN users u ON s.user_id=u.id ORDER BY s.created_at DESC LIMIT 30"
    ).fetchall()
    conn.close()
    return jsonify([dict(p) for p in purchases])


@app.route('/api/admin/all_transactions', methods=['GET'])
@admin_required
def api_admin_all_transactions():
    conn = get_db()
    transactions = conn.execute(
        "SELECT t.*, u.username FROM transactions t JOIN users u ON t.user_id=u.id ORDER BY t.created_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return jsonify([dict(t) for t in transactions])


# ======================== Health Check ========================
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})


# ======================== Main ========================
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
