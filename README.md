# شحن كروت فكة - Fakka Shop

تطبيق ويب لشحن كروت فكة فودافون مصر مبني بـ Flask.

## المميزات
- شحن كروت فكة فودافون لأي رقم
- نظام نجوم (عملة افتراضية) للمستخدمين
- لوحة تحكم أدمن كاملة
- تصميم احترافي متجاوب مع الموبايل
- اتصال مباشر بـ API فودافون

## النشر على Railway

1. ارفع المشروع على GitHub
2. اربط Railway بـ GitHub repo
3. Railway هيشتغل تلقائي (Procfile موجود)

## متغيرات البيئة (اختيارية)

| المتغير | الافتراضي | الوصف |
|---------|----------|-------|
| `SECRET_KEY` | fakka-shop-secret-key-2026 | مفتاح تشفير الجلسات |
| `PORT` | 8000 | منفذ التشغيل |
| `DB_PATH` | fakka_shop.db | مسار قاعدة البيانات |

## بيانات الدخول الافتراضية

- **أدمن:** admin / admin123
- **تجريبي:** test / admin123 (50 نجمة)

## التشغيل المحلي

```bash
pip install -r requirements.txt
python main.py
```

ثم افتح: http://localhost:8000

## API Endpoints

| Endpoint | Method | الوصف |
|----------|--------|-------|
| `/` | GET | الصفحة الرئيسية |
| `/health` | GET | فحص حالة السيرفر |
| `/api/login` | POST | تسجيل الدخول |
| `/api/logout` | POST | تسجيل الخروج |
| `/api/me` | GET | بيانات المستخدم الحالي |
| `/api/products` | GET | قائمة المنتجات |
| `/api/charge` | POST | شحن كرت فكة |
| `/api/transactions` | GET | سجل العمليات |
| `/api/admin/stats` | GET | إحصائيات الأدمن |
| `/api/admin/users` | GET | قائمة المستخدمين |
| `/api/admin/add_user` | POST | إضافة مستخدم |
| `/api/admin/add_stars` | POST | إضافة نجوم |
| `/api/admin/star_price` | GET/POST | سعر النجمة |
