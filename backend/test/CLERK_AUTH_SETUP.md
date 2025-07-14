# Clerk Authentication Setup Guide

This guide explains how to set up Clerk JWT authentication for the Cliplink backend.

## Prerequisites

1. A Clerk account and application set up
2. PostgreSQL database
3. Python environment with FastAPI

## Installation

1. **Install required dependencies:**
```bash
pip install PyJWT==2.8.0 cryptography==41.0.7
```

2. **Set environment variables:**
```bash
# Required for Clerk authentication
export CLERK_DOMAIN=your-clerk-domain.clerk.accounts.dev
export JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json

# Database (if not already set)
export DATABASE_URL=postgresql+asyncpg://username:password@localhost/cliplink_db

# CORS (if not already set)
export ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

3. **Run database migration:**
```bash
psql -d your_database -f migrate_to_clerk.sql
```

## Usage

### Protected Routes

Use the `get_current_user` dependency for routes that require authentication:

```python
from fastapi import Depends
from app.auth import get_current_user
from app.models import User

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.email}!"}
```

### Optional Authentication

Use `get_optional_user` for routes that work with or without authentication:

```python
from typing import Optional
from app.auth import get_optional_user

@app.get("/public")
async def public_route(user: Optional[User] = Depends(get_optional_user)):
    if user:
        return {"message": f"Hello {user.email}!"}
    else:
        return {"message": "Hello anonymous user!"}
```

### Frontend Integration

Send the Clerk JWT token in the Authorization header:

```javascript
const response = await fetch('/api/protected', {
  headers: {
    'Authorization': `Bearer ${await getToken()}`
  }
});
```

## API Endpoints

### User Management

- `GET /api/users/me` - Get current user profile
- `PUT /api/users/me` - Update user profile
- `GET /api/users/me/stats` - Get user statistics
- `GET /api/users/dashboard` - Protected dashboard endpoint
- `GET /api/users/public-info` - Public endpoint with optional auth

### Video Management (Protected)

- `GET /api/videos` - Get user's videos
- `GET /api/videos/{video_id}` - Get video details
- `POST /api/videos/{video_id}/clips/{clip_id}/view` - Log clip view

## Error Handling

The authentication system returns appropriate HTTP status codes:

- `401 Unauthorized` - Invalid or expired token
- `500 Internal Server Error` - Database or server errors

## Logging

The system logs authentication events:

- User creation: `"Created new user: user@example.com (clerk_id: user_123)"`
- User updates: `"Updated user data for user@example.com: {'first_name': 'John'}"`
- Token verification: `"Successfully verified token for user: user_123"`

## Security Features

- JWT signature verification using Clerk's JWKS endpoint
- Automatic user creation and synchronization
- Proper error handling with secure error messages
- Database session management
- Optional audience validation bypass (as requested)

## Troubleshooting

### Common Issues

1. **"CLERK_DOMAIN environment variable not set"**
   - Set the CLERK_DOMAIN environment variable

2. **"Invalid token" errors**
   - Check that the frontend is sending the correct JWT token
   - Verify the Clerk domain and JWKS URL are correct

3. **Database connection errors**
   - Ensure DATABASE_URL is set correctly
   - Check database connectivity

4. **CORS issues**
   - Add your frontend URL to ALLOWED_ORIGINS

### Debug Mode

Enable debug logging to see detailed authentication information:

```python
import logging
logging.getLogger("app.auth").setLevel(logging.DEBUG)
``` 