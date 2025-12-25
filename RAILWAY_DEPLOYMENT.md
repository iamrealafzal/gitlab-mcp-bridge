# Railway Deployment Guide

This guide will help you deploy the GitLab MCP Bridge to Railway.

## Prerequisites

1. A Railway account (https://railway.app)
2. A GitHub/GitLab repository with your code
3. A PostgreSQL database (Railway can provision this)

## Deployment Steps

### 1. Create a New Project on Railway

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository

### 2. Add Environment Variables

In Railway dashboard, go to your project → Variables, and add:

```
SECRET_KEY=your-django-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-app-name.railway.app,localhost,127.0.0.1
```

**Generate a SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Add PostgreSQL Database

1. In Railway dashboard, click "New" → "Database" → "Add PostgreSQL"
2. Railway will automatically set the `DATABASE_URL` environment variable
3. The app will use this automatically

### 4. Generate Encryption Key

The app uses encryption for sensitive data. Generate a key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add it as an environment variable:
```
ENCRYPTION_KEY=your-generated-key-here
```

**Note:** You'll need to update the code to read this from environment variables. Currently, it's stored in `.encryption_key` file.

### 5. Deploy

Railway will automatically:
- Install dependencies from `requirements.txt`
- Run migrations
- Start the app using the `Procfile`

### 6. Verify Deployment

1. Check the deployment logs in Railway
2. Visit your app URL (provided by Railway)
3. Access Django Admin at: `https://your-app.railway.app/admin/`

## Important Notes

### Static Files

Static files are served using WhiteNoise. Make sure to run:

```bash
python manage.py collectstatic --noinput
```

This is typically done automatically during Railway's build process.

### Database Migrations

Migrations run automatically during deployment. If you need to run them manually:

```bash
railway run python manage.py migrate
```

### Environment Variables

All sensitive data should be stored as Railway environment variables:
- `SECRET_KEY`
- `ENCRYPTION_KEY`
- `DATABASE_URL` (automatically set by Railway)
- Any API keys for LLM providers

### Custom Domain

To add a custom domain:
1. Go to your service → Settings → Domains
2. Add your custom domain
3. Update `ALLOWED_HOSTS` to include your domain

## Troubleshooting

### Migration Errors

If you see migration errors:
```bash
railway run python manage.py makemigrations
railway run python manage.py migrate
```

### Gunicorn Not Found

Make sure `gunicorn` is in `requirements.txt` (it should be).

### Static Files Not Loading

Ensure WhiteNoise is in `requirements.txt` and `MIDDLEWARE` includes `whitenoise.middleware.WhiteNoiseMiddleware`.

### Database Connection Issues

Check that `DATABASE_URL` is set correctly. Railway sets this automatically when you add a PostgreSQL database.

## Updating the App

Simply push to your repository, and Railway will automatically redeploy.

```bash
git push origin master
```

