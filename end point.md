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

## 🏢 Hostels, Rooms & Amenities

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/hostels/hostels/` | List all hostels |
| **GET** | `/api/hostels/hostels/{id}/` | Get hostel details |
| **GET** | `/api/hostels/images/` | List all hostel images |
| **GET** | `/api/hostels/images/{id}/` | Get hostel image details |
| **GET** | `/api/hostels/types/` | List all hostel types |
| **GET** | `/api/hostels/types/{id}/` | Get hostel type details |
| **GET** | `/api/hostels/types/{slug}/hostels/` | List hostels by category |
| **GET** | `/api/rooms/room-types/` | List room types |
| **GET** | `/api/rooms/room-types/{id}/` | Get room type details |
| **GET** | `/api/rooms/beds/` | List available beds |
| **GET** | `/api/rooms/beds/{id}/` | Get bed details |
| **GET** | `/api/amenities/` | List all amenities |
| **GET** | `/api/amenities/{id}/` | Get amenity details |

---

## 📍 Locations

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/locations/countries/` | List countries |
| **GET** | `/api/locations/countries/{id}/` | Get country details |
| **GET** | `/api/locations/states/` | List states |
| **GET** | `/api/locations/states/{id}/` | Get state details |
| **GET** | `/api/locations/cities/` | List cities |
| **GET** | `/api/locations/cities/{id}/` | Get city details |
| **GET** | `/api/locations/areas/` | List areas |
| **GET** | `/api/locations/areas/{id}/` | Get area details |
| **GET** | `/api/locations/search/?q=value` | Search hostels/locations |
| **GET** | `/api/locations/cities/{slug}/hostels/` | Hostels in a specific city |

---

## 📅 Bookings & Reviews (`/api/bookings/` & `/api/reviews/`)

| Method | Endpoint | Description | Sample Body |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/bookings/` | List my bookings (Auth Req) | None |
| **GET** | `/api/bookings/{id}/` | Get booking details | None |
| **POST** | `/api/bookings/` | Create a booking | `{"hostel": 1, "room_type": 1, "check_in": "2024-04-01", "guest_name": "John Doe", "mobile_number": "1234567890", "guest_age": 25}` |
| **GET** | `/api/reviews/` | List reviews | None |
| **GET** | `/api/reviews/{id}/` | Get review details | None |
| **POST** | `/api/reviews/` | Post a review | `{"hostel": 1, "rating": 5, "comment": "Great stay!"}` |

---

## 💳 Payments & Subscriptions (`/api/payments/`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/payments/` | List payments |
| **GET** | `/api/payments/{id}/` | Get payment details |
| **GET** | `/api/payments/subscriptions/` | List subscription plans |
| **GET** | `/api/payments/subscriptions/{id}/` | Get subscription plan details |

---

## 📄 CMS & Blog (`/api/cms/` & `/api/blog/`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/cms/terms-and-conditions/` | Terms and conditions |
| **GET** | `/api/cms/privacy-policy/` | Privacy policy |
| **GET** | `/api/cms/faq-categories/` | List FAQ categories |
| **GET** | `/api/cms/faqs/` | List FAQs |
| **GET** | `/api/cms/faqs/search/?q=value` | Search FAQs |
| **GET** | `/api/cms/faqs/{slug}/` | Get FAQ details |
| **GET** | `/api/blog/blog/` | Blog page data |
| **GET** | `/api/blog/blog/posts/` | List blog posts |
| **GET** | `/api/blog/blog/posts/{slug}/` | Get blog post details |
| **GET** | `/api/blog/blog/categories/` | List blog categories |

---

## 🌐 Public Pages (`/api/publicpages/`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/publicpages/homepage/` | Homepage content |
| **GET** | `/api/publicpages/landingpage/` | Landing page content |
| **GET** | `/api/publicpages/about/` | About page content |
| **GET** | `/api/publicpages/contact/` | Contact page content |
| **POST**| `/api/publicpages/contact/message/` | Send contact message |
| **GET** | `/api/publicpages/pricing/` | Pricing info |
| **GET** | `/api/publicpages/admin/homepage/` | Admin homepage content |
| **GET** | `/api/publicpages/admin/whyus/` | Admin why us content |

---

## 🛠️ Metadata

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/schema/` | OpenAPI schema |
| **GET** | `/api/schema/swagger-ui/` | Interactive API Docs (Swagger) |
| **GET** | `/api/schema/redoc/` | Interactive API Docs (ReDoc) |
| **GET** | `/api/seo/` | SEO Metadata |
| **GET** | `/api/seo/{id}/` | Get SEO Metadata details |
