# Frontend API Endpoints

This document provides a comprehensive list of all API endpoints directly called by the Next.js frontend application, logically grouped by their respective services.

---

## 🔐 Auth (`services/auth.service.ts` & `lib/auth.ts`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/api/auth/login/` | User login to receive tokens |
| **POST** | `/api/auth/register/` | User registration |
| **POST** | `/api/auth/logout/` | User logout and clear cookies |
| **POST** | `/api/auth/refresh/` | Refresh access token via cookie |
| **GET** | `/api/auth/me/` | Get current authenticated user info |
| **POST** | `/api/auth/verify-email/` | Verify user email with OTP code |
| **POST** | `/api/auth/send-otp/` | Send phone OTP to user |
| **POST** | `/api/auth/verify-otp/` | Verify phone OTP |

## 👤 User & Dashboard (`services/user.service.ts`, `services/dashboard.service.ts`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/users/me/` | Get user profile |
| **PATCH**| `/api/users/me/` | Update user profile |
| **GET** | `/api/dashboard/stats/` | Get dashboard statistics |

## 🏢 Hostels (`services/hostel.service.ts`, `services/hostel-image.service.ts`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/hostels/hostels/` | List all hostels |
| **GET** | `/api/hostels/hostels/{slug}/` | Get hostel details by slug |
| **GET** | `/api/hostels/hostels/my-hostels/` | List user's hostels |
| **GET** | `/api/hostels/hostels/my-hostels/{id}/` | Get user's specific hostel |
| **POST** | `/api/hostels/hostels/` | Create a new hostel |
| **PATCH**| `/api/hostels/hostels/my-hostels/{id}/update/` | Update user's hostel |
| **DELETE**| `/api/hostels/hostels/my-hostels/{id}/delete/` | Delete user's hostel |
| **POST** | `/api/hostels/images/` | Upload hostel image |
| **PATCH**| `/api/hostels/images/{id}/` | Update hostel image |
| **DELETE**| `/api/hostels/images/{id}/` | Delete hostel image |

## 🛏️ Rooms & Amenities (`services/room.service.ts`, `services/amenity.service.ts`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/rooms/room-types/my-rooms/` | List user's rooms |
| **GET** | `/api/rooms/room-types/grouped-my-rooms/`| List user's grouped rooms |
| **POST** | `/api/rooms/room-types/` | Create room type |
| **PATCH**| `/api/rooms/room-types/{id}/` | Update room type |
| **DELETE**| `/api/rooms/room-types/{id}/` | Delete room type |
| **GET** | `/api/amenities/` | List all amenities |

## 📅 Bookings & Payments (`services/booking.service.ts`, `services/payment.service.ts`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/bookings/owner/` | Get bookings for owner |
| **POST** | `/api/bookings/` | Create a booking |
| **PATCH**| `/api/bookings/{id}/` | Update booking status |
| **DELETE**| `/api/bookings/{id}/` | Delete a booking |
| **POST** | `/api/bookings/checkin/` | Check-in a booking |
| **POST** | `/api/bookings/send_otp/` | Send booking OTP |
| **POST** | `/api/bookings/verify_otp/`| Verify booking OTP |
| **POST** | `/api/payments/create_razorpay_order/` | Create Razorpay order |
| **POST** | `/api/payments/verify_razorpay_payment/`| Verify Razorpay payment |
| **POST** | `/api/payments/subscriptions/` | Create subscription |
| **GET** | `/api/payments/subscriptions/current/` | Get current subscription |
| **GET** | `/api/payments/` | Get payment list |

## 📍 Locations (`services/location.service.ts`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/locations/states/` | List states |
| **GET** | `/api/locations/cities/` | List cities |
| **GET** | `/api/locations/areas/` | List areas |
| **POST** | `/api/locations/cities/` | Create city |
| **POST** | `/api/locations/areas/` | Create area |

## 📄 CMS & Blog (`services/cms.service.ts`, `services/blog.service.ts`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/cms/faq-categories/` | Get FAQ categories |
| **GET** | `/api/cms/faqs/` | Get FAQs (with optional 'q' or 'category' params) |
| **GET** | `/api/cms/faqs/search/` | Search FAQs with 'q' param |
| **GET** | `/api/cms/faqs/{slug}/` | Get FAQ details by slug |
| **GET** | `/api/blog/blog/` | Get blog hero data |
| **GET** | `/api/blog/blog/posts/` | Get blog posts |
| **GET** | `/api/blog/blog/posts/{slug}/` | Get blog post by slug |
| **GET** | `/api/blog/blog/categories/` | Get blog categories |

## 🌐 Public Pages & Admin (`services/public.service.ts`, `services/admin.service.ts`, etc.)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/publicpages/homepage/` | Fetch homepage data |
| **GET** | `/api/publicpages/landingpage/` | Fetch landing page data |
| **GET** | `/api/publicpages/about/` | Fetch about page data |
| **GET** | `/api/publicpages/contact/` | Fetch contact page data |
| **GET** | `/api/publicpages/pricing/` | Fetch pricing page data |
| **POST** | `/api/publicpages/contact/message/`| Send contact form message |
| **PATCH**| `/api/publicpages/admin/homepage/{id}/`| Update homepage data (Admin) |
| **DELETE**| `/api/publicpages/admin/whyus/{id}/` | Delete why-us item (Admin) |
