# SEVA Arogya - Default Login Credentials

## 🔐 Demo Login Credentials

Use any of these credentials to log in:

### Option 1: Doctor Account
```
Email: doctor@hospital.com
Password: password123
```

### Option 2: Admin Account
```
Email: admin@seva.com
Password: admin123
```

### Option 3: Demo Account
```
Email: demo@demo.com
Password: demo
```

### Option 4: Any Credentials (Demo Mode)
```
Email: [any email]
Password: [any password]
```

The application is currently in demo mode and will accept any email/password combination for testing purposes.

---

## 🚀 Quick Login

1. Go to: http://localhost:5000/login
2. Enter one of the credentials above
3. Click "Login"
4. You'll be redirected to the home page

---

## ⚠️ Important Notes

- These are **demo credentials only**
- The current authentication is a **placeholder**
- In production, this will be replaced with **AWS Cognito**
- No actual password validation is performed (demo mode)
- Sessions are stored in Flask's session management

---

## 🔒 Production Authentication

When moving to production, the following will be implemented:

1. **AWS Cognito** for user authentication
2. **JWT tokens** for secure session management
3. **Password hashing** with bcrypt
4. **MFA (Multi-Factor Authentication)** support
5. **OAuth 2.0** for social sign-in (Google, Apple)
6. **Password reset** functionality
7. **Account lockout** after failed attempts
8. **Audit logging** for all authentication events

---

## 📝 Current Implementation

The login endpoint (`/api/v1/auth/login`) currently:
- Accepts any email/password combination
- Sets a Flask session with user_id
- Returns success response
- Redirects to home page

**Code location:** `app.py` - `api_login()` function

---

## 🔄 Testing Different Users

You can test with different email addresses to simulate multiple users:
- `doctor1@hospital.com`
- `doctor2@hospital.com`
- `sarah.mitchell@clinic.com`
- etc.

Each email will create a separate session.

---

**For development/testing only. Not for production use.**
