# 🏨 Hbackend — OYO for Hostels: Project Analysis Report

> **Generated:** 2026-02-25
> **Stack:** Django 6.0 · DRF · MySQL · SimpleJWT · Next.js Frontend
> **Status:** Early-stage — models defined, no API endpoints, no serializers, no tests

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Security Issues (Critical → Low)](#2-security-issues)
3. [Database Model Improvements](#3-database-model-improvements)
4. [Missing Files & Infrastructure](#4-missing-files--infrastructure)
5. [Required `.md` Files — What to Create](#5-required-md-files)
6. [Action Checklist](#6-action-checklist)

---

## 1. Executive Summary

The project has a **solid app-level architecture** with well-separated Django apps (`accounts`, `hostels`, `rooms`, `bookings`, `payments`, `reviews`, `amenities`, `locations`, `seo`, `cms`). However, it is at a very early stage:

- ❌ **No API views, serializers, or URL routes** (all `views.py` are empty, no `serializers.py`, only admin URL exists)
- ❌ **No tests written** (all `tests.py` are empty)
- ❌ **No `.gitignore`** — `.env`, `media/`, `staticfiles/`, `__pycache__/` could be committed
- ❌ **No `requirements.txt` or `pyproject.toml`** — dependencies are not tracked
- ❌ **No README.md** — project has no documentation
- ⚠️ **Several critical security issues** detailed below
- ⚠️ **Database models are functional but missing important fields** for a production hostel platform

---

## 2. Security Issues

### 🔴 CRITICAL

#### 2.1 `.env` Contains Hardcoded Secrets & Is Unprotected
```
SECRET_KEY = 'django-insecure--s7_)1g@6_kyeb2bxp4b0vvr-a_9c@uuor%d)-z)@&8ee@35l='
DB_PASSWORD=linus@12345
```
**Problems:**
- The `SECRET_KEY` still contains `django-insecure-` prefix — it is the default generated key
- Database password `linus@12345` is hardcoded and weak
- No `.gitignore` exists, so `.env` will be committed to version control

**Fix:**
- Generate a strong, random `SECRET_KEY` (use `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- Use a strong, unique database password
- Create `.gitignore` immediately (see Section 4)

---

#### 2.2 `DEBUG = True` is Hardcoded
```python
DEBUG = True
```
**Problem:** This is not read from `.env` — when deployed, it will leak stack traces, SQL queries, and internal paths.

**Fix:**
```python
DEBUG = config("DEBUG", default=False, cast=bool)
```

---

#### 2.3 `ALLOWED_HOSTS` is Empty
```python
ALLOWED_HOSTS = []
```
**Problem:** In production with `DEBUG=False`, this will reject all requests. With `DEBUG=True`, Django allows `localhost` and `127.0.0.1` only, but it's still a risk.

**Fix:**
```python
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=lambda v: [s.strip() for s in v.split(",")])
```

---

### 🟠 HIGH

#### 2.4 No Rate Limiting / Throttling
**Problem:** No `DEFAULT_THROTTLE_CLASSES` or `DEFAULT_THROTTLE_RATES` in `REST_FRAMEWORK` settings. An attacker can brute-force login, spam bookings, or scrape all hostel data.

**Fix — Add to `settings.py`:**
```python
REST_FRAMEWORK = {
    # ... existing settings ...
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "100/minute",
    },
}
```

---

#### 2.5 No Default Permission Classes
**Problem:** DRF defaults to `AllowAny` if no `DEFAULT_PERMISSION_CLASSES` is specified. This means every endpoint (once created) will be publicly accessible unless explicitly locked down.

**Fix:**
```python
REST_FRAMEWORK = {
    # ... existing settings ...
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
```

---

#### 2.6 No CORS Credentials Support
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
```
**Problem:** Missing `CORS_ALLOW_CREDENTIALS = True` if using cookie-based auth alongside JWT. Also needs to be environment-driven for production.

**Fix:**
```python
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000",
    cast=lambda v: [s.strip() for s in v.split(",")]
)
CORS_ALLOW_CREDENTIALS = True
```

---

#### 2.7 JWT Refresh Token Rotation Not Configured
**Problem:** `SIMPLE_JWT` lacks `ROTATE_REFRESH_TOKENS` and `BLACKLIST_AFTER_ROTATION`. Stolen refresh tokens remain valid for 7 days.

**Fix:**
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),  # Reduce from 30
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Also add to INSTALLED_APPS:
"rest_framework_simplejwt.token_blacklist",
```

---

### 🟡 MEDIUM

#### 2.8 Missing Security Headers in Settings
**Present (good):**
```python
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
```

**Missing — Add these for production:**
```python
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000         # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)
```

---

#### 2.9 No Input Validation at Model Level
**Problem:** Several fields accept any value:
- `Review.rating` — no `MinValueValidator(1)` / `MaxValueValidator(5)` → users can submit rating = -999
- `Booking.guests_count` — no minimum → can be 0 or negative
- `Payment.status` — plain `CharField` with no choices → any string accepted

---

#### 2.10 The `User` Model Lacks Security Fields
**Problem:**
- No email verification flow (only `is_verified` flag exists, no mechanism)
- No `profile_image` field
- No `date_of_birth` for age verification (important for hostel bookings)
- The `"admin"` role is commented out — admin checks would rely solely on `is_staff`/`is_superuser`

---

### 🟢 LOW

#### 2.11 Database Uses Root User
```
DB_USER=root
```
**Problem:** Using `root` for the application database user gives full MySQL privileges. Create a dedicated user with only the necessary permissions.

---

#### 2.12 No Logging Configuration
**Problem:** No `LOGGING` dict in settings. In production you won't capture security events, failed logins, or errors.

---

## 3. Database Model Improvements

### 3.1 `accounts.User` — Enhanced User Model
| Field | Issue | Recommendation |
|-------|-------|---------------|
| `phone` | No validation | Add `RegexValidator` for phone format |
| `email` | Inherited, not required | Make `email` unique and required |
| Missing | No profile picture | Add `avatar = ImageField(upload_to="avatars/", blank=True, null=True)` |
| Missing | No date of birth | Add `date_of_birth = DateField(null=True, blank=True)` |
| Missing | No gender field | Add for hostel matching (male/female/mixed hostels) |
| Missing | No soft delete | Add `is_deleted = BooleanField(default=False)` |
| Missing | No `updated_at` | Add `updated_at = DateTimeField(auto_now=True)` |
| `role` | Limited choices | Consider adding `"admin"` role back, or use Django Groups/Permissions |

---

### 3.2 `hostels.Hostel` — Core Model
| Field | Issue | Recommendation |
|-------|-------|---------------|
| `price` | Ambiguous meaning | Rename to `starting_price` or `min_price_per_night` (price lives on `RoomType`) |
| `owner` | `on_delete=CASCADE` | Use `PROTECT` — deleting a user shouldn't delete all their hostels silently |
| `city` | `on_delete=CASCADE` | Use `PROTECT` — deleting a city shouldn't wipe all hostels |
| `area` | `on_delete=CASCADE` | Use `SET_NULL` (already nullable) |
| Missing | No `updated_at` | Add `updated_at = DateTimeField(auto_now=True)` |
| Missing | No hostel type | Add `hostel_type` choices: `("male", "Male"), ("female", "Female"), ("mixed", "Mixed")` |
| Missing | No `phone` / `email` | Contact info for the hostel itself |
| Missing | No `website_url` | Hostel's own website |
| Missing | No policies | `cancellation_policy`, `house_rules` (TextField) |
| Missing | No `max_guests` | Total capacity of the hostel |
| `rating_avg` | Manual maintenance | Consider computing from `reviews` via annotation or signal instead of a stored field |

---

### 3.3 `rooms.RoomType` — Needs More Detail
| Field | Issue | Recommendation |
|-------|-------|---------------|
| Missing | No room count | Add `total_rooms = PositiveIntegerField()` — how many rooms of this type? |
| Missing | No `beds_per_room` | Important for hostels (dorms have 4/6/8/12 beds) |
| Missing | No images | Add a `RoomImage` model mirroring `HostelImage` |
| Missing | No gender restriction | Add `gender = CharField(choices=[("male","Male"),("female","Female"),("mixed","Mixed")])` |
| Missing | No room amenities | M2M to `Amenity` (some rooms have AC, lockers, etc.) |
| `base_price` | No per-night indication | Rename to `price_per_night` for clarity |
| Missing | No `updated_at` | Add `updated_at = DateTimeField(auto_now=True)` |

---

### 3.4 `rooms.Bed` — Expand For Hostel Use-Case
| Field | Issue | Recommendation |
|-------|-------|---------------|
| Missing | No bed type | Add `bed_type` — `upper_bunk`, `lower_bunk`, `single`, `double` |
| Missing | No pricing variance | Some beds cost more (lower bunk premium) — add optional `price_override` |
| Missing | No room reference | Beds belong to a `RoomType`, but in real hostels, beds belong to specific room instances. Consider adding a `Room` model between `RoomType` and `Bed`. |

---

### 3.5 `bookings.Booking` — Incomplete
| Field | Issue | Recommendation |
|-------|-------|---------------|
| Missing | No `bed` reference | For hostels you book a **bed**, not a room. Add `bed = ForeignKey(Bed, null=True, blank=True, on_delete=SET_NULL)` |
| Missing | No `special_requests` | Add `special_requests = TextField(blank=True)` |
| Missing | No `updated_at` | Add `updated_at = DateTimeField(auto_now=True)` |
| `status` | Incomplete choices | Add: `"checked_in"`, `"checked_out"`, `"no_show"`, `"refunded"` |
| Missing | No `cancellation_reason` | Useful for analytics |
| Missing | No `booking_source` | Track where bookings come from: `"website"`, `"app"`, `"walk-in"` |
| `check_in`/`check_out` | No validation | Model-level validation that `check_out > check_in` is missing. Add `clean()` method. |
| Missing | No overbooking prevention | No `unique_together` or constraint to prevent double-booking the same bed |

---

### 3.6 `payments.Payment` — Needs Expansion
| Field | Issue | Recommendation |
|-------|-------|---------------|
| `status` | No choices defined | Add `STATUS_CHOICES = ("pending","success","failed","refunded")` |
| `provider` | No choices/validation | Define `PROVIDER_CHOICES = ("razorpay","stripe","cash","upi")` |
| Missing | No `payment_method` | `"upi"`, `"card"`, `"netbanking"`, `"cash"` |
| Missing | No `currency` | Add `currency = CharField(max_length=3, default="INR")` |
| Missing | No `refund_amount` | Partial refunds are common |
| Missing | No `updated_at` | Track payment status changes |
| Missing | No `razorpay_order_id` | If using Razorpay, store the order ID for verification |

---

### 3.7 `reviews.Review` — Incomplete
| Field | Issue | Recommendation |
|-------|-------|---------------|
| `rating` | No validation | Add `validators=[MinValueValidator(1), MaxValueValidator(5)]` |
| Missing | No `updated_at` | Reviews can be edited |
| Missing | No `is_approved` | Moderation flag |
| Missing | No sub-ratings | Consider separate ratings for `cleanliness`, `location`, `staff`, `value_for_money` |
| Missing | No uniqueness constraint | Users can leave unlimited reviews for same hostel. Add `unique_together = ("hostel", "user")` |
| Missing | No `title` field | Review title/headline |

---

### 3.8 `amenities.Amenity` — Too Simple
| Field | Issue | Recommendation |
|-------|-------|---------------|
| Missing | No `category` | Group amenities: `"basic"`, `"safety"`, `"entertainment"`, `"food"` |
| Missing | No `description` | Explain what the amenity includes |
| Missing | No `is_active` | Ability to hide amenities without deleting |
| `icon` | Plain CharField | Consider storing icon class name (e.g., `"fa-wifi"`) or an `ImageField` |

---

### 3.9 `locations` Models — Minor Issues
| Model | Issue | Recommendation |
|-------|-------|---------------|
| `Area.slug` | Not globally unique | Good — uses `unique_together = ("slug", "city")` ✅ |
| `Country` | Missing `is_active` | To disable countries without deleting |
| All | Missing `created_at` / `updated_at` | Add timestamps for audit trail |

---

### 3.10 Missing Models Entirely
These models are **essential** for an OYO-like hostel platform but don't exist yet:

| Model | Purpose |
|-------|---------|
| `Coupon` / `Discount` | Promo codes, seasonal pricing |
| `WishList` / `SavedHostel` | User favorites |
| `Notification` | Push/email notification records |
| `SupportTicket` | Guest support / complaints |
| `HostelPolicy` | Structured policies (cancellation, pet, smoking) |
| `SeasonalPricing` | Dynamic pricing based on date range |
| `RoomAvailability` | Date-wise room/bed availability calendar |
| `GuestDocument` | ID proof upload for check-in verification |

---

## 4. Missing Files & Infrastructure

### 4.1 `.gitignore` — **Must Create**
```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
*.egg-info/
dist/
build/
*.egg

# Virtual Environment
venv/
.venv/
env/

# Django
*.sqlite3
db.sqlite3
/staticfiles/
/media/
*.log

# Environment
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

### 4.2 `requirements.txt` — **Must Create**
Run: `pip freeze > requirements.txt`

### 4.3 Per-App `urls.py` — **Must Create**
Every app needs its own `urls.py` with a router for API endpoints.

### 4.4 Per-App `serializers.py` — **Must Create**
Every app needs serializers for DRF endpoints.

### 4.5 `permissions.py` — **Must Create**
Custom permissions like `IsHostelOwner`, `IsBookingOwner`, `IsAdminOrReadOnly`.

---

## 5. Required `.md` Files

### 5.1 `README.md` (project root — `Hbackend/README.md`)
Should contain:
- Project description ("OYO-like hostel booking platform")
- Tech stack (Django 6.0, DRF, MySQL, SimpleJWT)
- Architecture diagram (apps and their relationships)
- Setup instructions (clone, create venv, install deps, create `.env`, migrate, runserver)
- API documentation link (drf-spectacular is installed but unused)
- Environment variables documentation
- Deployment guide

### 5.2 `CONTRIBUTING.md`
- Code style guidelines
- Branch naming convention
- PR process
- Commit message format

### 5.3 `API.md` or use drf-spectacular
- Since `drf_spectacular` is already in `INSTALLED_APPS`, configure it:
```python
# settings.py
SPECTACULAR_SETTINGS = {
    "TITLE": "Hostel Booking API",
    "DESCRIPTION": "OYO-like hostel booking platform API",
    "VERSION": "1.0.0",
}
```
- Add to `urls.py`:
```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
```

### 5.4 `CHANGELOG.md`
- Track version history and breaking changes

### 5.5 `DEPLOYMENT.md`
- Production deployment checklist
- Environment variable reference
- Database migration strategy
- Static file serving (whitenoise/nginx)

---

## 6. Action Checklist

### 🔴 Do Immediately (Security)
- [ ] Create `.gitignore`
- [ ] Generate a new strong `SECRET_KEY` and update `.env`
- [ ] Use a strong database password
- [ ] Set `DEBUG = config("DEBUG", default=False, cast=bool)`
- [ ] Set `ALLOWED_HOSTS` from env
- [ ] Add `DEFAULT_PERMISSION_CLASSES` to DRF settings
- [ ] Add throttling to DRF settings
- [ ] Configure JWT refresh token rotation + blacklist
- [ ] Add missing security headers

### 🟠 Do Before Building APIs (Models)
- [ ] Add `updated_at` to all models
- [ ] Add validators to `Review.rating`, `Booking.guests_count`
- [ ] Add `status` choices to `Payment`
- [ ] Add `clean()` validation to `Booking` (check_out > check_in)
- [ ] Change `on_delete=CASCADE` to `PROTECT` on `Hostel.owner` and `Hostel.city`
- [ ] Add `unique_together` constraint on `Review` (hostel + user)
- [ ] Make `User.email` unique and required
- [ ] Add `hostel_type` (male/female/mixed) to `Hostel`
- [ ] Add double-booking prevention constraints

### 🟡 Do Before MVP Launch (Infrastructure)
- [ ] Create `requirements.txt`
- [ ] Create `README.md`
- [ ] Create `serializers.py` for each app
- [ ] Create `urls.py` for each app & wire them in `Hbackend/urls.py`
- [ ] Create custom permissions (`permissions.py`)
- [ ] Write tests
- [ ] Configure `drf-spectacular` for API docs
- [ ] Set up logging configuration
- [ ] Create a dedicated MySQL user (not root)

### 🟢 Do For Production-Ready (Advanced)
- [ ] Add `Coupon`, `WishList`, `Notification`, `RoomAvailability` models
- [ ] Add `SeasonalPricing` model
- [ ] Implement email verification flow
- [ ] Add Celery for async tasks (email, notifications)
- [ ] Add Redis for caching
- [ ] Configure `DEPLOYMENT.md`
- [ ] Set up CI/CD pipeline
- [ ] Add rate limiting per endpoint
- [ ] Implement soft delete across models

---

> **Bottom Line:** Your app structure is well-organized, but you need to harden security settings, enrich your models with validation and missing fields, and create essential project documentation before building out the API layer.
