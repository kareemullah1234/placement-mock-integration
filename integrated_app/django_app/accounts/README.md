# 🚀 Accounts App - User Management & Authentication

The `accounts` app is the core authentication module for the Placement Portal. It handles user registration, role detection, login/logout, and profile initialization for both **Candidates** and **Companies**.

---

## ✨ Key Features

- **Custom User Model**: Extends Django's `AbstractUser` with a `role` field.
- **Auto-Role Detection**: Automatically assigns roles based on the user's email domain during registration:
  - 🎓 **Candidate**: `@gmail.com`, `@yahoo.com`, `@outlook.com`
  - 🏢 **Company**: Any other business or professional domain (e.g., `@microsoft.com`, `@startup.io`).
- **Unified Login**: A single login portal that redirects users to their specific dashboard based on their profile type.
- **REST API Support**: Includes JSON-based endpoints for mobile or frontend integration:
  - `/api/register/` (Register a new user)
  - `/api/login/` (Authenticate and get user info)

---

## 🛠️ Architecture

### Models
- **User**: The central authentication model.
- **Profile Connection**:
  - If role is `candidate`, a `CandidateProfile` is automatically created in the `candidates` app.
  - If role is `company`, a `CompanyProfile` is automatically created in the `companies` app.

### Endpoints
| Path | Action | Name |
| :--- | :--- | :--- |
| `/accounts/register/` | Web Registration | `register` |
| `/accounts/login/` | Web Login | `login` |
| `/accounts/logout/` | Logout | `logout` |
| `/accounts/dashboard/` | Common Dashboard | `dashboard` |
| `/accounts/redirect/` | Role-based Redirector | `role_redirect` |
| `/accounts/api/register/` | JSON Registration | (API only) |
| `/accounts/api/login/` | JSON Login | (API only) |

---

## 🧪 Testing Suite

This app includes a robust testing suite with **100 automated test cases** covering:
- ✅ Domain-specific role assignment.
- ✅ API registration and login success/failure.
- ✅ Username integrity (dots, dashes, underscores).
- ✅ Superuser and Profile-based redirection logic.

### Running Tests
To execute the account tests, run the following command from the root `django_app` directory:
```bash
python manage.py test accounts
```

---

## 🎨 Templates
The app uses styled HTML templates located in `templates/accounts/`:
- `login.html`: A modern, centered login interface.
- `register.html`: A clean registration form.

---
*Created by MOHAMMED-KAIF-M*
