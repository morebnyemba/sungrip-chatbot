from django.test import TestCase
from django.utils import timezone
from customers.models import Customer
from conversations.models import Contact
from .models import QuoteRequest, Quote


class QuoteRequestModelTests(TestCase):
    """Tests for QuoteRequest model."""

    def setUp(self):
        """Set up test data."""
        self.customer = Customer.objects.create(
            phone_number='+1234567890',
            full_name='John Doe',
            email='john@example.com'
        )
        
        self.contact = Contact.objects.create(
            whatsapp_id='1234567890',
            phone_number='+1234567890',
            profile_name='John Doe'
        )

    def test_quote_request_creation(self):
        """Test creating a quote request."""
        quote_request = QuoteRequest.objects.create(
            customer=self.customer,
            contact=self.contact,
            request_id='QUOTE-20260208094500',
            customer_name='John Doe',
            monthly_bill=150.00,
            roof_type='tile',
            location='Harare, Zimbabwe',
            status='pending'
        )
        
        self.assertEqual(quote_request.customer, self.customer)
        self.assertEqual(quote_request.contact, self.contact)
        self.assertEqual(quote_request.customer_name, 'John Doe')
        self.assertEqual(float(quote_request.monthly_bill), 150.00)
        self.assertEqual(quote_request.roof_type, 'tile')
        self.assertEqual(quote_request.location, 'Harare, Zimbabwe')
        self.assertEqual(quote_request.status, 'pending')

    def test_quote_request_without_customer(self):
        """Test creating a quote request without a linked customer."""
        quote_request = QuoteRequest.objects.create(
            contact=self.contact,
            request_id='QUOTE-20260208094501',
            customer_name='Jane Smith',
            monthly_bill=200.00,
            roof_type='metal',
            location='Bulawayo, Zimbabwe'
        )
        
        self.assertIsNone(quote_request.customer)
        self.assertEqual(quote_request.contact, self.contact)
        self.assertEqual(quote_request.customer_name, 'Jane Smith')

    def test_quote_request_str(self):
        """Test string representation of quote request."""
        quote_request = QuoteRequest.objects.create(
            customer=self.customer,
            request_id='QUOTE-20260208094502',
            customer_name='John Doe',
            monthly_bill=150.00
        )
        
        expected_str = f"Quote Request QUOTE-20260208094502 - John Doe"
        self.assertEqual(str(quote_request), expected_str)

    def test_quote_request_status_choices(self):
        """Test that all status choices work correctly."""
        quote_request = QuoteRequest.objects.create(
            customer=self.customer,
            request_id='QUOTE-20260208094503',
            customer_name='John Doe'
        )
        
        # Test all status transitions
        for status_code, status_name in QuoteRequest.STATUS_CHOICES:
            quote_request.status = status_code
            quote_request.save()
            self.assertEqual(quote_request.status, status_code)

    def test_quote_request_quote_link(self):
        """Test linking quote request to a quote."""
        # Create a quote
        quote = Quote.objects.create(
            customer=self.customer,
            quote_number='Q-001',
            status='draft'
        )
        
        # Create quote request and link it
        quote_request = QuoteRequest.objects.create(
            customer=self.customer,
            request_id='QUOTE-20260208094504',
            customer_name='John Doe',
            monthly_bill=150.00,
            status='converted',
            quote=quote
        )
        
        self.assertEqual(quote_request.quote, quote)
        self.assertIn(quote_request, quote.source_requests.all())

    def test_quote_request_ordering(self):
        """Test that quote requests are ordered by created_at descending."""
        # Create multiple quote requests
        qr1 = QuoteRequest.objects.create(
            request_id='QUOTE-20260208094505',
            customer_name='First'
        )
        qr2 = QuoteRequest.objects.create(
            request_id='QUOTE-20260208094506',
            customer_name='Second'
        )
        qr3 = QuoteRequest.objects.create(
            request_id='QUOTE-20260208094507',
            customer_name='Third'
        )
        
        # Get all quote requests
        quote_requests = list(QuoteRequest.objects.all())
        
        # Check ordering (newest first)
        self.assertEqual(quote_requests[0], qr3)
        self.assertEqual(quote_requests[1], qr2)
        self.assertEqual(quote_requests[2], qr1)

