# Cliplink Backend API

This directory contains the FastAPI backend service for Cliplink AI, providing endpoints for managing YouTube video submissions and retrieving processed clips.

## Features

- **Video Management**: CRUD operations for YouTube video submissions
- **Clip Tracking**: Management of generated video clips with S3 URLs
- **View Analytics**: Logging and tracking of clip views
- **Database**: Async SQLAlchemy with PostgreSQL
- **API Documentation**: Auto-generated OpenAPI/Swagger docs

## Directory Structure

```
backend/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── auth.py              # Authentication module (placeholder)
│   ├── database.py          # Database configuration (SQLAlchemy)
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy models
│   └── schemas.py           # Pydantic schemas
├── requirements.txt         # Python dependencies
├── schema.sql              # PostgreSQL database schema
└── sample_queries.sql      # Example database queries
```

## Setup Instructions

### 1. Environment Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

Ensure PostgreSQL is running and create the database:

```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database and user
CREATE DATABASE cliplink;
CREATE USER cliplink_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE cliplink TO cliplink_user;

-- Create UUID extension
\c cliplink
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Run the schema
\i schema.sql
```

### 3. Environment Variables

Create a `.env` file in the backend directory:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://cliplink_user:your_password@localhost:5432/cliplink
DB_ECHO=false

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Server Configuration
PORT=8000
ENV=development
```

### 4. Running the Application

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- `GET /health` - Service health and database connectivity

### Video Management
- `GET /api/videos` - Get paginated list of videos
- `GET /api/videos/{video_id}` - Get detailed video information with clips

### Analytics
- `POST /api/videos/{video_id}/clips/{clip_id}/view` - Log clip view event

## Authentication

**Currently disabled** - All endpoints are open access. Authentication can be implemented later.

## Database Models

### Video
- **id**: UUID primary key
- **user_id**: UUID (for future user association)
- **youtube_id**: YouTube video identifier
- **title**: Video title
- **status**: Processing status (pending, processing, done, failed)
- **created_at**: Timestamp

### Clip
- **id**: UUID primary key
- **video_id**: UUID foreign key to Video
- **s3_url**: S3 URL of the processed clip
- **start_time**: Start time in seconds
- **end_time**: End time in seconds
- **duration**: Duration in seconds
- **created_at**: Timestamp

### ClipViewLog
- **id**: UUID primary key
- **user_id**: UUID (viewer)
- **clip_id**: UUID foreign key to Clip
- **viewed_at**: Timestamp

## Development

### Code Formatting
```bash
black app/
```

### Testing
```bash
pytest
```

### Database Migrations
The application automatically creates tables on startup. For production, consider using Alembic for proper migrations.

## Integration

This backend integrates with:
1. **PostgreSQL Database** - for data persistence
2. **Frontend Application** - via CORS-enabled API

## Troubleshooting

### Common Issues

1. **Database Connection Error**: Check PostgreSQL is running and DATABASE_URL is correct
2. **CORS Issues**: Verify ALLOWED_ORIGINS includes your frontend URL

### Logs

Check application logs for detailed error information. Enable database logging with `DB_ECHO=true` for SQL debugging. 