"""
Order and installation models for Sungrip Solar
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from customers.models import Customer
from products.models import Product, SolarPackage


class Quote(models.Model):
    """Customer quote for solar installation"""
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='quotes')
    quote_number = models.CharField(max_length=50, unique=True)
    
    # Requirements
    estimated_monthly_bill = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    average_daily_usage_kwh = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    roof_type = models.CharField(max_length=50, blank=True)
    available_roof_space = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="in square meters")
    
    # System recommendation
    recommended_system_size_kw = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    recommended_package = models.ForeignKey(SolarPackage, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    installation_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('sent', 'Sent to Customer'),
            ('viewed', 'Viewed by Customer'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
        ],
        default='draft'
    )
    
    # Validity
    valid_until = models.DateField(null=True, blank=True)
    
    # Notes
    internal_notes = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='quotes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Quote'
        verbose_name_plural = 'Quotes'
    
    def __str__(self):
        return f"Quote {self.quote_number} - {self.customer.full_name}"


class QuoteItem(models.Model):
    """Items in a quote"""
    
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name = 'Quote Item'
        verbose_name_plural = 'Quote Items'
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


class Order(models.Model):
    """Customer order for solar installation"""
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    installation_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Payment'),
            ('confirmed', 'Confirmed'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('unpaid', 'Unpaid'),
            ('partial', 'Partially Paid'),
            ('paid', 'Fully Paid'),
            ('refunded', 'Refunded'),
        ],
        default='unpaid'
    )
    
    # Dates
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Notes
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
    
    def __str__(self):
        return f"Order {self.order_number} - {self.customer.full_name}"
    
    @property
    def balance_due(self):
        return self.total_amount - self.paid_amount


class OrderItem(models.Model):
    """Items in an order"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


class Installation(models.Model):
    """Solar installation tracking"""
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='installation')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='installations')
    
    # Installation details
    installation_address = models.TextField()
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # System information
    system_size_kw = models.DecimalField(max_digits=6, decimal_places=2)
    number_of_panels = models.IntegerField()
    inverter_model = models.CharField(max_length=200, blank=True)
    battery_capacity_kwh = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Scheduling
    scheduled_date = models.DateField(null=True, blank=True)
    estimated_duration_days = models.IntegerField(default=1)
    actual_start_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    
    # Team assignment
    lead_technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='lead_installations')
    team_members = models.ManyToManyField(User, related_name='team_installations', blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('on_hold', 'On Hold'),
            ('cancelled', 'Cancelled'),
        ],
        default='scheduled'
    )
    
    # Documentation
    pre_installation_photos = models.JSONField(default=list, blank=True)
    post_installation_photos = models.JSONField(default=list, blank=True)
    installation_certificate = models.FileField(upload_to='certificates/', null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    completion_notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Installation'
        verbose_name_plural = 'Installations'
    
    def __str__(self):
        return f"Installation for {self.customer.full_name} - {self.system_size_kw}kW"

