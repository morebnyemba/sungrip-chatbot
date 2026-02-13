# Security Considerations for Sungrip Solar Chatbot

## Overview

This document outlines security best practices and considerations for deploying and maintaining the Sungrip Solar Chatbot system.

## Environment Variables & Secrets

### Critical Security Requirements

1. **Never commit `.env` files** to version control
   - The `.env.example` file is provided as a template
   - Copy it to `.env` and fill in your actual values
   - `.env` is in `.gitignore` and should never be committed

2. **Generate Strong Secrets**

   ```bash
   # Generate Django SECRET_KEY
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   
   # Generate random passwords
   openssl rand -base64 32
   ```

3. **Required Environment Variables**
   - `SECRET_KEY`: Django secret key (required in production)
   - `DB_PASSWORD`: Database password (required)
   - `REDIS_PASSWORD`: Redis password (required)

4. **Production Checklist**
   - [ ] Set `DEBUG=False`
   - [ ] Set strong `SECRET_KEY`
   - [ ] Set proper `ALLOWED_HOSTS`
   - [ ] Use strong database passwords (20+ characters)
   - [ ] Use strong Redis password
   - [ ] Configure HTTPS/SSL
   - [ ] Set WhatsApp credentials
   - [ ] Review and remove default passwords

## Database Security

### PostgreSQL

1. **Password Protection**
   - Use strong, unique passwords
   - Rotate passwords regularly
   - Never use default passwords

2. **Network Access**
   - In production, restrict database port (5432) to internal network only
   - Remove port mapping from docker-compose.yml if not needed
   - Use firewall rules to limit access

3. **Backups**
   ```bash
   # Regular backups (recommended: daily)
   docker compose exec db pg_dump -U sungrip_user sungrip_db > backup.sql
   
   # Encrypted backup
   docker compose exec db pg_dump -U sungrip_user sungrip_db | gpg --encrypt > backup.sql.gpg
   ```

4. **Encryption at Rest**
   - Consider using encrypted volumes in production
   - PostgreSQL supports TLS for connections
   - Enable database-level encryption if available in your hosting environment

## API Security

### Authentication

1. **JWT Tokens**
   - Tokens expire after 24 hours (configurable)
   - Refresh tokens rotate on use
   - Old tokens are blacklisted after rotation

2. **Password Requirements**
   - Django's built-in password validators are enabled
   - Minimum length, complexity requirements enforced
   - Common passwords are rejected

3. **Rate Limiting** (To Be Implemented)
   ```python
   # Recommended: django-ratelimit
   # Add to settings.py:
   REST_FRAMEWORK = {
       'DEFAULT_THROTTLE_CLASSES': [
           'rest_framework.throttling.AnonRateThrottle',
           'rest_framework.throttling.UserRateThrottle'
       ],
       'DEFAULT_THROTTLE_RATES': {
           'anon': '100/hour',
           'user': '1000/hour'
       }
   }
   ```

### CORS Protection

1. **Configure Allowed Origins**
   ```env
   CORS_ALLOWED_ORIGINS=https://zimgrow.shop
   ```

2. **Never Use Wildcards in Production**
   ```python
   # WRONG - Never do this in production:
   CORS_ALLOW_ALL_ORIGINS = True
   
   # RIGHT - Specify exact domains:
   CORS_ALLOWED_ORIGINS = ['https://zimgrow.shop']
   ```

## WhatsApp Security

### Webhook Security

1. **Signature Verification** (To Be Implemented)
   ```python
   # Verify webhook signatures from Meta
   import hmac
   import hashlib
   
   def verify_signature(payload, signature, app_secret):
       expected = hmac.new(
           app_secret.encode('utf-8'),
           payload.encode('utf-8'),
           hashlib.sha256
       ).hexdigest()
       return hmac.compare_digest(signature, f'sha256={expected}')
   ```

2. **HTTPS Only**
   - Meta requires HTTPS for webhooks
   - Use Let's Encrypt for free SSL certificates
   - Never use self-signed certificates

3. **Verify Token**
   - Use a strong, random verify token
   - Never reuse tokens across environments
   - Store in environment variables, not in code

### Credentials Storage

1. **Current Implementation**
   - WhatsApp credentials stored in database (WhatsAppConfig model)
   - ⚠️ **WARNING**: Access tokens stored in plain text

2. **Recommended: Encrypt Sensitive Fields**
   ```bash
   # Install django-encrypted-model-fields
   pip install django-encrypted-model-fields
   
   # Add to settings.py
   FIELD_ENCRYPTION_KEY = os.environ.get('FIELD_ENCRYPTION_KEY')
   
   # Update models.py
   from encrypted_model_fields.fields import EncryptedCharField
   
   class WhatsAppConfig(models.Model):
       access_token = EncryptedCharField(max_length=500)
       app_secret = EncryptedCharField(max_length=200)
   ```

3. **Alternative: Use Environment Variables**
   - Store credentials in environment variables instead of database
   - More secure for single-instance deployments
   - Less flexible for multi-tenant setups

## SSL/TLS Configuration

### Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot

# Stop nginx to free port 80
docker compose stop nginx

# Generate certificate for frontend domain
sudo certbot certonly --standalone \
  -d zimgrow.shop \
  --email your-email@example.com \
  --agree-tos --no-eff-email

# Generate certificate for backend API domain
sudo certbot certonly --standalone \
  -d api.zimgrow.shop \
  --email your-email@example.com \
  --agree-tos --no-eff-email

# Restart nginx
docker compose up -d nginx

# Certificates saved to:
# /etc/letsencrypt/live/zimgrow.shop/
# /etc/letsencrypt/live/api.zimgrow.shop/
```

### Nginx SSL Configuration

The `nginx_proxy/nginx.conf` is already configured with separate server blocks:
- `zimgrow.shop` — serves the React frontend
- `api.zimgrow.shop` — serves the Django backend API, admin panel, and webhook

See `nginx_proxy/nginx.conf` for the full configuration.

## Data Protection

### Personal Data (GDPR/POPIA Compliance)

1. **Customer Data**
   - Collect only necessary information
   - Implement data retention policies
   - Provide data export functionality
   - Enable data deletion on request

2. **Encryption**
   - Encrypt data at rest (database, backups)
   - Encrypt data in transit (HTTPS, TLS)
   - Encrypt sensitive fields in database

3. **Access Control**
   - Implement role-based access control
   - Log all access to customer data
   - Regular access audits

### WhatsApp Messages

1. **Message Storage**
   - Store only necessary message data
   - Implement retention policies
   - Consider anonymization for analytics

2. **Media Files**
   - Scan uploaded files for malware
   - Implement file size limits
   - Restrict file types
   - Store media in secure location

## Application Security

### Django Security Settings

```python
# Production settings.py

# Security
SECURE_SSL_REDIRECT = True  # Redirect HTTP to HTTPS
SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
CSRF_COOKIE_SECURE = True  # Only send CSRF cookie over HTTPS
SECURE_HSTS_SECONDS = 31536000  # HSTS policy
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Sessions
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hour

# CSRF
CSRF_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = True
```

### Input Validation

1. **Django Forms/Serializers**
   - Always validate user input
   - Use Django's built-in validators
   - Implement custom validators for business logic

2. **File Uploads**
   ```python
   # Validate file uploads
   from django.core.validators import FileExtensionValidator
   
   class DocumentUpload(models.Model):
       file = models.FileField(
           validators=[FileExtensionValidator(['pdf', 'jpg', 'png'])]
       )
   ```

### SQL Injection Prevention

- ✅ Using Django ORM (automatic protection)
- ❌ Never use raw SQL with user input
- ❌ Never construct queries with string concatenation

```python
# WRONG - SQL injection vulnerability
User.objects.raw(f"SELECT * FROM users WHERE id = {user_id}")

# RIGHT - Use parameterized queries
User.objects.raw("SELECT * FROM users WHERE id = %s", [user_id])

# BEST - Use ORM
User.objects.get(id=user_id)
```

## Monitoring & Logging

### Security Logging

1. **Log Security Events**
   - Failed login attempts
   - Permission denied errors
   - API authentication failures
   - Admin actions

2. **Log Analysis**
   - Monitor for unusual patterns
   - Alert on suspicious activity
   - Regular security audits

3. **Don't Log Sensitive Data**
   - Never log passwords
   - Never log full credit card numbers
   - Never log API tokens
   - Sanitize logs before storage

### Recommended Tools

```python
# settings.py - Logging configuration
LOGGING = {
    'version': 1,
    'handlers': {
        'security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/sungrip/security.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

## Incident Response

### Security Incident Plan

1. **Detection**
   - Monitor logs for suspicious activity
   - Set up alerts for security events
   - Regular security audits

2. **Response**
   - Document the incident
   - Contain the threat
   - Assess the impact
   - Notify affected users if required

3. **Recovery**
   - Restore from backups if needed
   - Patch vulnerabilities
   - Update security measures

4. **Prevention**
   - Analyze root cause
   - Implement fixes
   - Update documentation
   - Train team

### Contact Information

For security issues:
- Email: security@sungrip.com
- Do not publicly disclose security vulnerabilities
- Use responsible disclosure practices

## Regular Security Maintenance

### Monthly Tasks
- [ ] Review access logs
- [ ] Check for failed login attempts
- [ ] Review user permissions
- [ ] Update dependencies

### Quarterly Tasks
- [ ] Rotate database passwords
- [ ] Review API tokens
- [ ] Security audit
- [ ] Penetration testing (recommended)

### Annually
- [ ] Full security assessment
- [ ] Disaster recovery drill
- [ ] Update security policies
- [ ] Team security training

## Security Checklist for Production

Before going live:

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` set
- [ ] Database passwords are strong and unique
- [ ] Redis password is strong
- [ ] HTTPS/SSL configured and working
- [ ] Security headers configured in Nginx
- [ ] WhatsApp webhook signature verification implemented
- [ ] CORS properly configured (no wildcards)
- [ ] Backups configured and tested
- [ ] Monitoring and logging in place
- [ ] Rate limiting implemented
- [ ] Security patches applied to all dependencies
- [ ] Remove default/test accounts
- [ ] Firewall rules configured
- [ ] Sensitive data encryption implemented
- [ ] Incident response plan documented

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [WhatsApp Business API Security](https://developers.facebook.com/docs/whatsapp/overview/security/)
- [POPIA Compliance](https://popia.co.za/)
