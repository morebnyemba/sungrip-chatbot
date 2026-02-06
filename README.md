# Sungrip Solar Chatbot System

A comprehensive WhatsApp-based chatbot system for Sungrip Solar Energy Company, specializing in solar system installation, maintenance, and supply. Built with Django REST Framework backend, React frontend, and WhatsApp Business API integration.

## 🌟 Features

### Core Features
- **WhatsApp Integration**: Full WhatsApp Business API integration for customer conversations
- **Customer Management**: Complete CRM for tracking customer interactions and profiles
- **Product Catalog**: Manage solar panels, inverters, batteries, and accessories
- **Quote System**: Generate and send quotes for solar installations
- **Order Management**: Track orders from creation to completion
- **Installation Tracking**: Monitor installation progress with GPS coordinates
- **AI-Powered Support**: Google Gemini AI integration for intelligent responses
- **Multi-User System**: Role-based access for admins, technicians, and sales staff

### Solar-Specific Features
- **System Sizing Calculator**: Recommend appropriate solar system sizes based on customer needs
- **Pre-configured Packages**: Ready-made solar packages for different customer types
- **Installation Scheduling**: Schedule and assign installation teams
- **Photo Documentation**: Before/after photos for installations
- **Warranty Management**: Track warranties for installed systems
- **Location Tracking**: GPS coordinates for all installations

## 🏗️ Architecture

### Technology Stack

**Backend:**
- Django 4.2+ with Django REST Framework
- PostgreSQL 15 (Database)
- Redis 7 (Cache & Celery Broker)
- Celery (Background Tasks)
- WhatsApp Business API
- Google Gemini AI

**Frontend:**
- React 18+
- Tailwind CSS
- shadcn/ui Components
- React Query (Data Fetching)

**Infrastructure:**
- Docker & Docker Compose
- Nginx (Reverse Proxy)
- Gunicorn (WSGI Server)

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Nginx Proxy                         │
│                 (SSL/TLS, Load Balancing)                   │
├────────────────────┬────────────────────────────────────────┤
│                    │                                        │
│  ┌─────────────────▼──────────────┐  ┌──────────────────┐  │
│  │     React Frontend             │  │  Django Backend   │  │
│  │  (Customer Interface)          │  │   (REST API)      │  │
│  └────────────────────────────────┘  └────────┬──────────┘  │
│                                               │             │
│              ┌────────────────────────────────┴─────┐       │
│              │                                      │       │
│       ┌──────▼────────┐                    ┌───────▼──────┐│
│       │  PostgreSQL   │                    │    Redis     ││
│       │  (Database)   │                    │   (Broker)   ││
│       └───────────────┘                    └───────┬──────┘│
│                                                    │       │
│                                         ┌──────────▼──────┐│
│                                         │ Celery Workers  ││
│                                         │  (Async Tasks)  ││
│                                         └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   WhatsApp Business API
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose installed
- WhatsApp Business Account
- (Optional) Google AI API key for AI features

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sungrip-chatbot
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**
   ```bash
   docker compose up -d
   ```

4. **Run database migrations**
   ```bash
   docker compose exec backend python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

6. **Access the application**
   - Frontend: http://localhost
   - Admin Panel: http://localhost/admin
   - API: http://localhost/api

## 📚 Documentation

### API Apps

#### Customers App
Manages customer profiles and interactions:
- **Customer**: Main customer profile with contact info and location
- **CustomerInteraction**: Track all touchpoints with customers

#### Products App
Solar equipment catalog:
- **ProductCategory**: Organize products into categories
- **Product**: Individual solar equipment items
- **SolarPackage**: Pre-configured solar system packages
- **PackageItem**: Products included in packages

#### Orders App
Order and installation management:
- **Quote**: Generate quotes for customers
- **QuoteItem**: Line items in quotes
- **Order**: Confirmed customer orders
- **OrderItem**: Products in orders
- **Installation**: Track installation progress

#### Conversations App
WhatsApp messaging:
- **Contact**: WhatsApp contacts
- **Conversation**: Message threads
- **Message**: Individual messages
- **MessageTemplate**: Reusable message templates

#### WhatsApp Integration App
WhatsApp Business API integration:
- **WhatsAppConfig**: API configuration
- **WebhookLog**: Webhook event logging

### Configuration

#### WhatsApp Setup

1. **Get WhatsApp Business API Credentials**
   - Sign up at https://business.facebook.com
   - Create a WhatsApp Business app
   - Get Phone Number ID, Access Token, and App Secret

2. **Configure Webhook**
   - Set webhook URL: `https://yourdomain.com/webhook/`
   - Set verify token (match WHATSAPP_VERIFY_TOKEN in .env)
   - Subscribe to message events

3. **Update Environment Variables**
   ```env
   WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
   WHATSAPP_ACCESS_TOKEN=your_access_token
   WHATSAPP_APP_SECRET=your_app_secret
   WHATSAPP_VERIFY_TOKEN=your_verify_token
   ```

#### AI Integration (Optional)

1. **Get Google AI API Key**
   - Visit https://makersuite.google.com/app/apikey
   - Create API key

2. **Update Environment**
   ```env
   GOOGLE_AI_API_KEY=your_api_key
   ```

## 🔧 Development

### Running Locally

**Backend Development:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

**Frontend Development:**
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend tests
docker compose exec backend python manage.py test

# Frontend tests
cd frontend && npm test
```

### Creating Migrations
```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

## 🔒 Security

- JWT authentication for API access
- CORS protection
- HTTPS/SSL encryption (in production)
- Environment-based secrets
- WhatsApp webhook signature verification
- SQL injection protection via Django ORM

## 📦 Deployment

### Production Checklist

1. **Update Environment Variables**
   - Set `DEBUG=False`
   - Generate secure `SECRET_KEY`
   - Set proper `ALLOWED_HOSTS`
   - Use strong database passwords

2. **SSL Certificate Setup**
   - Configure SSL certificates in nginx
   - Update nginx.conf for HTTPS

3. **Static Files**
   ```bash
   docker compose exec backend python manage.py collectstatic
   ```

4. **Database Backup**
   ```bash
   docker compose exec db pg_dump -U sungrip_user sungrip_db > backup.sql
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

Proprietary - Sungrip Solar Energy Company

## 📞 Support

For support and inquiries:
- Email: support@sungrip.com
- WhatsApp: +263 XXX XXX XXX

## 🎯 Roadmap

- [ ] Mobile app for technicians
- [ ] Real-time system monitoring integration
- [ ] Payment gateway integration (Paynow, EcoCash)
- [ ] Customer portal with system performance dashboards
- [ ] Automated appointment scheduling
- [ ] Inventory management system
- [ ] Advanced analytics and reporting

