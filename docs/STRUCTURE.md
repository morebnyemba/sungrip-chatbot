# Sungrip Solar Chatbot - Project Structure

## Directory Overview

```
sungrip-chatbot/
├── backend/                          # Django backend application
│   ├── sungrip_backend/             # Django project settings
│   │   ├── __init__.py
│   │   ├── settings.py              # Django settings (env-based config)
│   │   ├── urls.py                  # Main URL routing
│   │   ├── wsgi.py                  # WSGI config for production
│   │   ├── asgi.py                  # ASGI config for async
│   │   └── celery.py                # Celery configuration
│   │
│   ├── customers/                   # Customer management app
│   │   ├── models.py                # Customer, CustomerInteraction
│   │   ├── serializers.py           # DRF serializers
│   │   ├── views.py                 # API viewsets
│   │   ├── urls.py                  # URL routing
│   │   └── admin.py                 # Django admin config
│   │
│   ├── products/                    # Product catalog app
│   │   ├── models.py                # Product, ProductCategory, SolarPackage
│   │   ├── serializers.py           # DRF serializers
│   │   ├── views.py                 # API viewsets
│   │   ├── urls.py                  # URL routing
│   │   └── admin.py                 # Django admin config
│   │
│   ├── orders/                      # Order management app
│   │   ├── models.py                # Quote, Order, Installation
│   │   ├── serializers.py           # DRF serializers
│   │   ├── views.py                 # API viewsets
│   │   ├── urls.py                  # URL routing
│   │   └── admin.py                 # Django admin config
│   │
│   ├── conversations/               # WhatsApp messaging app
│   │   ├── models.py                # Contact, Conversation, Message
│   │   ├── serializers.py           # DRF serializers
│   │   ├── views.py                 # API viewsets
│   │   ├── urls.py                  # URL routing
│   │   └── admin.py                 # Django admin config
│   │
│   ├── whatsapp_integration/        # WhatsApp API integration
│   │   ├── models.py                # WhatsAppConfig, WebhookLog
│   │   ├── views.py                 # Webhook handlers
│   │   ├── services.py              # WhatsApp API client
│   │   ├── tasks.py                 # Celery tasks
│   │   └── admin.py                 # Django admin config
│   │
│   ├── Dockerfile                   # Backend container config
│   ├── entrypoint.sh                # Container startup script
│   ├── requirements.txt             # Python dependencies
│   └── manage.py                    # Django management script
│
├── frontend/                        # React frontend (to be implemented)
│   ├── src/
│   │   ├── components/              # Reusable UI components
│   │   ├── pages/                   # Page components
│   │   ├── services/                # API service layer
│   │   ├── context/                 # React context
│   │   └── App.jsx                  # Main app component
│   ├── Dockerfile                   # Frontend container config
│   └── package.json                 # Node dependencies
│
├── nginx_proxy/                     # Nginx reverse proxy
│   ├── nginx.conf                   # Nginx configuration
│   └── ssl/                         # SSL certificates (production)
│
├── docs/                            # Documentation
│   ├── API.md                       # API documentation
│   ├── SETUP.md                     # Setup & deployment guide
│   └── ARCHITECTURE.md              # Architecture documentation
│
├── docker-compose.yml               # Multi-container orchestration
├── .env.example                     # Environment template
├── .gitignore                       # Git ignore rules
├── quick-start.sh                   # Quick setup script
└── README.md                        # Project README

```

## Application Structure

### Backend Apps

#### 1. **customers** - Customer Relationship Management
**Purpose**: Manage customer profiles and track all interactions

**Models**:
- `Customer`: Main customer profile
  - Contact information (phone, email, WhatsApp)
  - Address and GPS coordinates
  - Customer classification (residential/commercial/industrial)
  - Creation and update timestamps

- `CustomerInteraction`: Interaction tracking
  - Type (inquiry, quote_request, support, etc.)
  - Channel (WhatsApp, phone, email, in-person)
  - Summary and details
  - Assigned staff member

**API Endpoints**:
- `GET /api/customers/` - List all customers
- `POST /api/customers/` - Create new customer
- `GET /api/customers/{id}/` - Get customer details
- `PUT /api/customers/{id}/` - Update customer
- `DELETE /api/customers/{id}/` - Delete customer
- `GET /api/interactions/` - List interactions
- `POST /api/interactions/` - Create interaction

#### 2. **products** - Solar Equipment Catalog
**Purpose**: Manage solar equipment inventory and packages

**Models**:
- `ProductCategory`: Product categorization
  - Hierarchical structure (parent/child categories)
  - Display order and icons

- `Product`: Individual products
  - Type (solar_panel, inverter, battery, etc.)
  - Specifications (JSON field for flexibility)
  - Pricing (cost and selling price)
  - Inventory tracking
  - Warranty information

- `SolarPackage`: Pre-configured systems
  - System size (kW)
  - Target audience (small home, business, etc.)
  - Total pricing
  - Included products

- `PackageItem`: Products in packages
  - Quantity and notes

**API Endpoints** (to be implemented):
- `GET /api/products/` - List products
- `GET /api/categories/` - List categories
- `GET /api/packages/` - List solar packages

#### 3. **orders** - Sales and Installation Management
**Purpose**: Manage quotes, orders, and installations

**Models**:
- `Quote`: Customer quotations
  - System sizing recommendations
  - Line items with pricing
  - Validity period
  - Status tracking

- `QuoteItem`: Products in quote

- `Order`: Confirmed orders
  - Payment tracking
  - Status workflow
  - Expected delivery dates

- `OrderItem`: Products in order

- `Installation`: Installation tracking
  - GPS coordinates
  - System specifications
  - Team assignment
  - Scheduling
  - Photo documentation
  - Status workflow

**API Endpoints** (to be implemented):
- `GET /api/quotes/` - List quotes
- `POST /api/quotes/` - Create quote
- `GET /api/orders/` - List orders
- `POST /api/orders/` - Create order
- `GET /api/installations/` - List installations

#### 4. **conversations** - WhatsApp Messaging
**Purpose**: Handle WhatsApp conversations and messages

**Models**:
- `Contact`: WhatsApp contacts
  - Link to Customer
  - WhatsApp ID
  - Opt-in status
  - Message statistics

- `Conversation`: Message threads
  - Status (active, pending, resolved, archived)
  - Assignment to staff
  - Last message timestamp

- `Message`: Individual messages
  - Type (text, image, document, etc.)
  - Direction (inbound/outbound)
  - Content and media
  - Status tracking
  - Reply chains

- `MessageTemplate`: Reusable templates
  - WhatsApp-approved templates
  - Multi-language support
  - Button configurations

**API Endpoints** (to be implemented):
- `GET /api/conversations/` - List conversations
- `GET /api/messages/` - List messages
- `POST /api/messages/` - Send message

#### 5. **whatsapp_integration** - WhatsApp Business API
**Purpose**: Interface with Meta WhatsApp Business API

**Models**:
- `WhatsAppConfig`: API configuration
  - Credentials (phone number ID, access token)
  - API version
  - Webhook settings

- `WebhookLog`: Webhook event logging
  - Event type
  - Payload
  - Processing status

**Components** (to be implemented):
- Webhook verification handler
- Message receive handler
- Message send service
- Media upload/download service
- Template message service

## Data Flow

### Customer Inquiry Flow

```
1. Customer sends WhatsApp message
   ↓
2. Meta webhook → /webhook/ endpoint
   ↓
3. Create/update Contact and Conversation
   ↓
4. Save Message to database
   ↓
5. Process message (AI or rule-based)
   ↓
6. Generate response
   ↓
7. Send via WhatsApp API
   ↓
8. Update conversation status
```

### Order Creation Flow

```
1. Customer expresses interest
   ↓
2. Create/update Customer record
   ↓
3. Gather requirements
   ↓
4. Create Quote with recommended system
   ↓
5. Send quote via WhatsApp
   ↓
6. Customer accepts
   ↓
7. Create Order from Quote
   ↓
8. Create Installation record
   ↓
9. Schedule installation
   ↓
10. Assign technician team
    ↓
11. Complete installation
    ↓
12. Upload photos and documentation
```

## Technology Choices

### Why Django?
- Mature, batteries-included framework
- Excellent ORM for complex data models
- Django Admin for rapid backend management
- Django REST Framework for robust APIs
- Large ecosystem of packages

### Why PostgreSQL?
- Robust relational database
- JSON field support for flexible data
- Full-text search capabilities
- Proven in production

### Why Redis + Celery?
- Async task processing for WhatsApp messages
- Scheduled tasks for reminders/notifications
- Background processing for AI responses
- Caching for performance

### Why Docker?
- Consistent development/production environment
- Easy deployment and scaling
- Isolated services
- Simple dependency management

## Security Considerations

### API Security
- JWT authentication for all API endpoints
- Token expiration and refresh
- CORS protection

### WhatsApp Security
- Webhook signature verification
- HTTPS-only communication
- Token-based authentication

### Database Security
- Password-protected connections
- Encrypted at rest (production)
- Regular backups
- No sensitive data in logs

### Environment Security
- All secrets in environment variables
- No secrets in version control
- Production vs development configs

## Scalability

### Horizontal Scaling
- Backend: Multiple Gunicorn workers
- Celery: Multiple worker instances
- Database: Read replicas (future)
- Redis: Cluster mode (future)

### Caching Strategy
- Redis for session caching
- Django cache framework
- Static file CDN (production)

### Performance Optimization
- Database indexing on frequent queries
- Query optimization with select_related/prefetch_related
- API pagination
- Compressed static files (WhiteNoise)

## Next Implementation Steps

1. **Complete REST APIs** for products, orders, quotes, installations
2. **WhatsApp Integration** - webhook handlers and message sending
3. **Conversational Flow Engine** - rule-based or AI-powered
4. **Frontend Dashboard** - React admin interface
5. **Payment Integration** - Paynow or other gateways
6. **Monitoring & Logging** - Application insights
7. **Testing** - Unit tests, integration tests
8. **CI/CD** - Automated deployment pipeline
