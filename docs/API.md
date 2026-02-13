# Sungrip Solar Chatbot API Documentation

## Base URL
```
Development: http://localhost:8000/api
Production: https://api.zimgrow.shop/api
```

## Authentication

The API uses JWT (JSON Web Token) authentication.

### Get Access Token
```http
POST /api/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Refresh Access Token
```http
POST /api/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Using the Token
Include the access token in the Authorization header:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## API Endpoints

### Customers

#### List Customers
```http
GET /api/customers/
Authorization: Bearer {token}
```

**Query Parameters:**
- `customer_type`: Filter by type (residential, commercial, industrial)
- `is_active`: Filter by active status (true/false)
- `province`: Filter by province
- `city`: Filter by city
- `search`: Search in name, phone, email, address
- `ordering`: Order by field (created_at, full_name, -created_at)

**Response:**
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/customers/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "phone_number": "+263771234567",
      "whatsapp_number": "+263771234567",
      "full_name": "John Doe",
      "email": "john@example.com",
      "address_line1": "123 Main Street",
      "address_line2": "",
      "city": "Harare",
      "province": "Harare",
      "postal_code": "12345",
      "gps_latitude": "-17.8216",
      "gps_longitude": "31.0492",
      "customer_type": "residential",
      "is_active": true,
      "notes": "Interested in 5kW system",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### Get Customer
```http
GET /api/customers/{id}/
Authorization: Bearer {token}
```

#### Create Customer
```http
POST /api/customers/
Authorization: Bearer {token}
Content-Type: application/json

{
  "phone_number": "+263771234567",
  "whatsapp_number": "+263771234567",
  "full_name": "John Doe",
  "email": "john@example.com",
  "customer_type": "residential",
  "address_line1": "123 Main Street",
  "city": "Harare",
  "province": "Harare"
}
```

#### Update Customer
```http
PUT /api/customers/{id}/
Authorization: Bearer {token}
Content-Type: application/json

{
  "full_name": "John Doe Updated",
  "notes": "Purchased 5kW system"
}
```

#### Delete Customer
```http
DELETE /api/customers/{id}/
Authorization: Bearer {token}
```

### Customer Interactions

#### List Interactions
```http
GET /api/interactions/
Authorization: Bearer {token}
```

**Query Parameters:**
- `customer`: Filter by customer ID
- `interaction_type`: inquiry, quote_request, follow_up, support, complaint, payment
- `channel`: whatsapp, phone, email, in_person
- `search`: Search in summary and details

**Response:**
```json
{
  "count": 50,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "customer": 1,
      "customer_name": "John Doe",
      "interaction_type": "inquiry",
      "channel": "whatsapp",
      "summary": "Asking about solar panel pricing",
      "details": "Customer wants quote for 5kW residential system",
      "handled_by": 2,
      "handled_by_name": "admin",
      "created_at": "2024-01-15T14:30:00Z"
    }
  ]
}
```

#### Create Interaction
```http
POST /api/interactions/
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer": 1,
  "interaction_type": "inquiry",
  "channel": "whatsapp",
  "summary": "Follow-up call about quote",
  "details": "Customer requested modifications to the quote",
  "handled_by": 2
}
```

## Products API

(To be implemented)

- `GET /api/products/` - List all products
- `GET /api/products/{id}/` - Get product details
- `GET /api/categories/` - List product categories
- `GET /api/packages/` - List solar packages

## Orders API

(To be implemented)

- `GET /api/quotes/` - List quotes
- `POST /api/quotes/` - Create quote
- `GET /api/orders/` - List orders
- `POST /api/orders/` - Create order
- `GET /api/installations/` - List installations

## WhatsApp Webhook

### Verify Webhook
```http
GET /webhook/?hub.mode=subscribe&hub.verify_token={token}&hub.challenge={challenge}
```

### Receive Messages
```http
POST /webhook/
Content-Type: application/json

{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "PHONE_NUMBER",
              "phone_number_id": "PHONE_NUMBER_ID"
            },
            "contacts": [
              {
                "profile": {
                  "name": "CUSTOMER_NAME"
                },
                "wa_id": "CUSTOMER_WHATSAPP_ID"
              }
            ],
            "messages": [
              {
                "from": "CUSTOMER_WHATSAPP_ID",
                "id": "MESSAGE_ID",
                "timestamp": "TIMESTAMP",
                "text": {
                  "body": "MESSAGE_CONTENT"
                },
                "type": "text"
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

## Error Responses

### 400 Bad Request
```json
{
  "field_name": [
    "This field is required."
  ]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error."
}
```

## Rate Limiting

(To be implemented)

- Rate limits will be applied per user/IP
- Default: 1000 requests per hour

## Pagination

All list endpoints support pagination:
- Default page size: 50 items
- Maximum page size: 100 items
- Use `?page=2` to navigate pages

## Filtering & Search

Most list endpoints support:
- **Filtering**: `?field_name=value`
- **Search**: `?search=query`
- **Ordering**: `?ordering=field_name` or `?ordering=-field_name` (descending)

## Best Practices

1. **Always use HTTPS** in production
2. **Store tokens securely** - never in localStorage for sensitive data
3. **Refresh tokens** before they expire
4. **Handle errors gracefully** - check status codes
5. **Use pagination** for large datasets
6. **Validate input** on the client side before sending

## Code Examples

### Python (requests)
```python
import requests

# Get token
response = requests.post('http://localhost:8000/api/token/', json={
    'username': 'admin',
    'password': 'password'
})
token = response.json()['access']

# Make authenticated request
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:8000/api/customers/', headers=headers)
customers = response.json()
```

### JavaScript (fetch)
```javascript
// Get token
const response = await fetch('http://localhost:8000/api/token/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'admin',
    password: 'password'
  })
});
const { access } = await response.json();

// Make authenticated request
const customersResponse = await fetch('http://localhost:8000/api/customers/', {
  headers: {
    'Authorization': `Bearer ${access}`
  }
});
const customers = await customersResponse.json();
```

### cURL
```bash
# Get token
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# Make authenticated request
curl -X GET http://localhost:8000/api/customers/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```
