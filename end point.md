# Backend API Endpoints

This document provides a comprehensive list of API endpoints for testing in Postman.

**Base URL:** `http://34.80.15.95`

---

## 🔐 Authentication Endpoints (`/api/auth/`)

| Method | Endpoint | Description | Sample Request Body |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/auth/register/` | Register a new user | `{"username": "johndoe", "email": "john@example.com", "password": "password123", "confirm_password": "password123"}` |
| **POST** | `/api/auth/login/` | Login & get tokens | `{"username": "john@example.com", "password": "password123"}` |
| **POST** | `/api/auth/verify-email/` | Verify email with code | `{"email": "john@example.com", "code": "123456"}` |
| **POST** | `/api/auth/send-otp/` | Send phone OTP (Auth Req) | `{"phone": "+1234567890"}` |
| **POST** | `/api/auth/verify-otp/` | Verify phone OTP (Auth Req) | `{"phone": "+1234567890", "code": "123456"}` |
| **GET** | `/api/auth/me/` | Current user info (Auth Req) | None |
| **POST** | `/api/auth/refresh/` | Refresh access token | None (uses Cookie) |
| **POST** | `/api/auth/logout/` | Logout & clear tokens | None |

---

## 👤 Accounts & Dashboard (`/api/accounts/` & `/api/dashboard/`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/accounts/users/` | List all users (Staff only) |
| **GET** | `/api/accounts/users/{id}/` | Get specific user profile |
| **GET** | `/api/users/me/` | Get current user profile |
| **GET** | `/api/dashboard/stats/` | Get dashboard statistics |

---

## 🏢 Hostels & Rooms

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/hostels/hostels/` | List all hostels |
| **GET** | `/api/hostels/hostels/{id}/` | Get hostel details |
| **GET** | `/api/hostels/types/{slug}/hostels/` | List hostels by category |
| **GET** | `/api/rooms/room-types/` | List room types |
| **GET** | `/api/rooms/beds/` | List available beds |
| **GET** | `/api/amenities/` | List all amenities |

---

## 📍 Locations

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/locations/countries/` | List countries |
| **GET** | `/api/locations/states/` | List states |
| **GET** | `/api/locations/cities/` | List cities |
| **GET** | `/api/locations/areas/` | List areas |
| **GET** | `/api/locations/search/?q=value` | Search hostels/locations |
| **GET** | `/api/locations/cities/{slug}/hostels/` | Hostels in a specific city |

---

## 📅 Bookings & Reviews (`/api/bookings/` & `/api/reviews/`)

| Method | Endpoint | Description | Sample Body |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/bookings/` | My bookings (Auth Req) | None |
| **POST** | `/api/bookings/` | Create a booking | `{"hostel": 1, "room_type": 1, "check_in": "2024-04-01", "guest_name": "John Doe", "mobile_number": "1234567890", "guest_age": 25}` |
| **GET** | `/api/reviews/` | List reviews | None |
| **POST** | `/api/reviews/` | Post a review | `{"hostel": 1, "rating": 5, "comment": "Great stay!"}` |

---

## 💳 Payments & Subscriptions (`/api/payments/`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/payments/` | List payments |
| **GET** | `/api/payments/subscriptions/` | List subscription plans |

---

## 📄 CMS & Blog (`/api/cms/` & `/api/blog/`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/cms/terms-and-conditions/` | Terms and conditions |
| **GET** | `/api/cms/privacy-policy/` | Privacy policy |
| **GET** | `/api/cms/faqs/` | List FAQs |
| **GET** | `/api/blog/blog/` | Blog page data |
| **GET** | `/api/blog/posts/` | List blog posts |

---

## 🌐 Public Pages (`/api/publicpages/`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/publicpages/homepage/` | Homepage content |
| **GET** | `/api/publicpages/landingpage/` | Landing page content |
| **POST** | `/api/publicpages/contact/message/` | Send contact message |
| **GET** | `/api/publicpages/pricing/` | Pricing info |

---

## 🛠️ Metadata

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/schema/swagger-ui/` | Interactive API Docs |
| **GET** | `/api/seo/` | SEO Metadata |
