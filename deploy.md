# 🚀 GCP Deployment Guide & API Reference

> [!WARNING]
> **Why is the Server Not Responding Locally/Currently?**
> Your `.env` file (`v...\App\Hbackend\.env`) has the `DATABASE_URL` variable commented out (Lines 10 & 11), while your `settings.py` actively requires it via `dj_database_url.parse(config("DATABASE_URL"))` on Line 142.
> 
> *Because Django cannot find this mandatory environment variable, the server will crash immediately upon startup.*
> 
> **Fix:** Add your new MySQL connection string to `.env` using this format:
> `DATABASE_URL=mysql://<db_user>:<db_password>@<db_host>:<db_port>/<db_name>`
> (Make sure to restart the server after saving the `.env` file).

---

## 🌐 1. Opening Page & Endpoints

Your Django application does **not** have a default traditional homepage registered to the root URL `/`. 
However, the default opening page for the backend, where you can view, explore, and test your new APIs is the **Swagger UI**.

- **Primary Opening Page (Swagger UI):** `http://<domain>/api/schema/swagger-ui/`
- **Alternative Docs (Redoc):** `http://<domain>/api/schema/redoc/`
- **Django Admin Panel:** `http://<domain>/admin/`

### 🔗 Master List of API Endpoints
All API business logic is categorized under the following base paths:

* `/api/auth/` ➔ Authentication Operations (Login, Register, OTP verification)
* `/api/accounts/` ➔ User Account & Profile Management
* `/api/amenities/` ➔ Available Hostel Amenities
* `/api/locations/` ➔ Valid Locations and Regions
* `/api/hostels/` ➔ Core Hostel Listing, details, and filtering
* `/api/rooms/` ➔ Room configurations, availability, and pricing
* `/api/bookings/` ➔ Handling Booking process and status
* `/api/reviews/` ➔ Customer Feedback & Rating System
* `/api/payments/` ➔ Integrated Payment Management (Razorpay)
* `/api/seo/` ➔ SEO Tags & Metadata Configuration
* `/api/cms/` ➔ Content Management System updates
* `/api/blog/` ➔ General Articles and blogging engine
* `/api/publicpages/` ➔ Landing Page configurations (About us, Contact, FAQs etc.)
* `/api/dashboard/stats/` ➔ Summary statistics for dashboard metrics
* `/api/users/me/` ➔ Details of the currently authenticated user session

---

## ☁️ 2. Proper Steps to Deploy on GCP (Google Cloud Run)

Since your project relies on a standard `.env` configuration and features a modular DRF architecture, using **Containerized Google Cloud Run** is highly recommended over App Engine Standard due to better scalability and seamless native integration with Cloud SQL.

### Step 1: Prepare the Google Cloud Environment
1. Log into your [Google Cloud Console](https://console.cloud.google.com/).
2. Select your Project, and ensure **Billing is enabled**.
3. Go to **APIs & Services** > **Library** and enable:
   - Cloud Run API
   - Cloud SQL Admin API
   - Cloud Build API
   - Secret Manager API (optional, to store Env vars securely)

### Step 2: Configure Cloud SQL (MySQL Database)
Since you mentioned you created a MySQL database:
1. If your database is inside GCP, navigate to **SQL** and ensure the instance is active.
2. Ensure you have your `db_user` and `db_password` configured.
3. Note the **Connection Name** of the instance (Format: `project-id:region:instance-name`).

### Step 3: Create a `Dockerfile`
At the root of your `Hbackend` folder, create a new file named `Dockerfile` to instruct GCP how to run the project.

```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set work directory
WORKDIR /app

# Install MySQL dependencies (required for mysqlclient)
RUN apt-get update \
    && apt-get install -y default-libmysqlclient-dev gcc pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Expose port
EXPOSE 8080

# Command to run Gunicorn
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 0 Hbackend.wsgi:application
```

### Step 4: Adjust Django Context (`settings.py`)
Ensure your `settings.py` is safely adjusted:
- **`ALLOWED_HOSTS`**: `["*"]` works, but for production, list your actual backend Cloud Run domain here.
- **`CSRF_TRUSTED_ORIGINS`**: Add `https://<YOUR-NEW-CLOUD-RUN-URL>.run.app`.

### Step 5: Deploy Using gcloud CLI
Ensure the **Google Cloud CLI** is installed on your local machine.

1. **Authenticate CLI**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
2. **Deploy the Django App**
   ```bash
   gcloud run deploy hostel-backend --source . --region us-central1 --allow-unauthenticated --port 8080
   ```
3. During deployment (or immediately after from the GCP Console), set all your **Environment Variables** (from your `.env` file) in the Cloud Run service settings. 
   - **Important**: Your `DATABASE_URL` should connect via Unix sockets natively to avoid connection limitations. Format (if hosted on GCP Cloud SQL):
     `mysql://root:password@/hosteldb?unix_socket=/cloudsql/project:region:instance_name`

### Step 6: Apply Database Migrations (Post-Deployment)
Once the Cloud Run container is built successfully, apply your previous local migrations to the production Database:
1. Connect locally to your Cloud SQL Proxy.
2. Run standard django migration logic:
   ```bash
   python manage.py migrate
   ```
   Or execute a **Cloud Run Job** directly targeted to run the command: `python manage.py migrate`.

---
> [!TIP]
> **Static Files Warning**: You already have WhiteNoise successfully integrated (`whitenoise.middleware.WhiteNoiseMiddleware` and `whitenoise.storage.CompressedManifestStaticFilesStorage`). To finalize the deployment, just ensure the static files are generated during the image construction process by optionally adding `RUN python manage.py collectstatic --noinput` to your Dockerfile right before the CMD line.
