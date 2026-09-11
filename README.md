# Leasify

A property management backend built with Django REST Framework. Leasify handles the full lifecycle of rental property management, from apartment listings and tenant onboarding to billing, payments, and notifications.

---

## Features

- **Apartments** — Full CRUD with role-based visibility, filtering, ordering, and an overview dashboard with occupancy and rent analytics
- **Tenancy** — Tenant onboarding, status lifecycle (reserved > active > defaulting > terminated), and role-based access control
- **Billing** — Billing period management with automatic status transitions and period completion logic
- **Payments** — M-Pesa STK push integration via Daraja API with idempotency, async callback processing, and manual payment recording
- **Authentication** — Session-based auth with email/password and Google OAuth (id_token flow), password reset, email verification, and throttling
- **Notifications** — Transactional email system with HTML and plain-text templates, centralized notification model with per-user read tracking
- **Roles & Permissions** — Granular permission system with manager, caretaker, and tenant roles, each with scoped access across all resources

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5, Django REST Framework |
| Database | PostgreSQL |
| Cache / Broker | Redis |
| Task Queue | Celery with Celery Beat |
| Auth | Django sessions, Google OAuth 2.0 |
| Payments | Safaricom Daraja (M-Pesa STK Push) |
| Email | SMTP with HTML/plain-text templates |
| Logging | Structlog |
| Monitoring | Sentry |
| Testing | pytest, pytest-django, factory-boy |

---

## Project Structure

```
leasify/
├── apps/
│   ├── api/              # Health check
│   ├── apartments/       # Apartment model, CRUD, overview analytics
│   ├── authentication/   # Login, logout, Google OAuth, password flows, email-verification
│   ├── billing/          # Billing periods, status transitions
│   ├── payments/         # M-Pesa STK push, callbacks, manual payments
│   ├── tenancy/          # Tenancy lifecycle management
│   └── users/            # User model, accounts, roles, permissions
├── common/
│   ├── domain.py         # FilterPolicy for selectors
│   ├── pagination.py     # Pagination helper
│   ├── period.py         # DateRange — date normalization utility
│   ├── views.py          # BaseView with utilities
│   ├── models.py         # Base model with default fields
│   ├── emails.py         # Centralized email sending
│   ├── exceptions.py     # Custom exception classes
│   └── models.py         # BaseModel with created_at/updated_at
├── fixtures/
│   ├── roles.json            # Role and permission fixtures
│   ├── test_apartments.json  # Development seed apartments
│   └── test_users.json       # Development seed users
├── templates/
│   ├── payments.json     # Sample receipt template(WeasyPrint)
│   └── emails/           # HTML and plain-text email templates
└── tests/                # Test suite mirroring app structure
config/
├── django/
│   ├── base.py           # Base settings
│   ├── production.py     # Production overrides
│   └── test.py           # Test overrides (MD5 hasher, fast setup)
├── settings/
│   ├── celery.py
│   ├── google.py
│   ├── logging.py
│   ├── mpesa.py
│   └── security.py
└── env.py                # django-environ instance
```

---

## Architecture

Leasify follows the [HackSoft Django Styleguide](https://github.com/HackSoftware/Django-Styleguide) — a service-oriented architecture with a clean separation of concerns:

- **Models** — data and constraints only, no business logic
- **Selectors** — read-only query functions, role-based filtering via `FilteringPolicy`
- **Services** — all write operations and business logic, always atomic
- **Views** — thin orchestration layer, delegates to selectors and services
- **Serializers** — input validation and output formatting only

```
Request → View → Serializer (validate) → Selector (read) → Service (write) → Response
```

---

## Payments Flow

```
Tenant initiates payment
  → STK push sent to M-Pesa (Daraja API)
  → Payment created with PENDING status
  → Tenant prompted on phone

M-Pesa callback arrives
  → IP validated at nginx level
  → Callback parsed and queued to Celery
  → 200 OK returned immediately to Safaricom

Celery processes callback (idempotent, retries on failure)
  → Payment status updated (SUCCESS / FAILED)
  → Billing period marked complete on success
  → Email notification sent to tenant and managers
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis

### Setup

```bash
# Clone the repo
git clone https://github.com/munene25/leasify.git
cd leasify

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements/local.txt

# Copy environment file
cp .env.example .env
# Fill in your values

# Option 1: [Manual]
# Run migrations
python manage.py migrate

# Seed roles and permissions
python manage.py setup_roles

# Seed development data (optional)
python manage.py runscript seed

# Option 2: [bash script]
chmod +x ./reset.sh
./reset.sh # This will reset db migrate and seed the db with test values.

# Start the development server
python manage.py runserver
```

### Running Celery

```bash
# Worker
celery -A leasify worker -l info

# Beat scheduler
celery -A leasify beat -l info
```

### Running Tests

```bash
pytest

# With coverage
pytest --cov=leasify --cov-report=term-missing
```

---

## API Overview

| Resource | Endpoints |
|---|---|
| Api | `GET /api/health/` |
| Authentication | `POST /auth/login/` `POST /auth/logout/` `POST /auth/google/login` `POST /auth/password/reset/` `POST /auth/refresh/` `POST /auth/password-change/` `POST /auth/password-reset/request` `POST /auth/password-reset/confirm` `POST /auth/email-verification/request` `POST /auth/email-verification/confirm` |
| Users | `GET /users/` `POST /users/` `GET /users/{id}/` `DELETE /users/{id}/` `GET /users/me/` `PATCH /users/me/` `DELETE users/me/` `GET /users/{id}/role` `PATCH /users/{id}/role` `DELETE /users/{id}/role` `GET /users/roles/` `POST /users/email-change` `POST /users/unsubscribe/{uuidb4}` |
| Apartments | `GET /apartments/` `POST /apartments/` `GET /apartments/{id}/` `PATCH /apartments/{id}/` `DELETE /apartments/{id}/` `GET /apartments/choices/` |
| Tenancy | `GET /tenancies/` `POST /tenancies/` `GET /tenancies/{id}/` `PATCH /tenancies/{id}/` |
| Billing | `GET /billings/` `GET /billings/{id}/` |
| Payments | `GET /payments/` `GET /payments/{id}/` `POST /payments/mpesa/initiate/` `POST /payments/alt/` `POST /payments/callback/mpesa/` `POST /payments/mpesa/query/` |

Full API documentation via Postman collection — coming soon.

---

## Roadmap

- [ ] Frontend (React — in progress)
- [ ] Docker / containerization
- [ ] OpenAPI / Swagger docs
- [ ] Push notifications
- [ ] Multi-property support

---

## Status

Backend complete. Frontend under active development.

---

*Built by Edwin Munene*
