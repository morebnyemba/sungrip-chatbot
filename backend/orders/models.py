"""
Order and installation models for Sungrip Solar
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from customers.models import Customer
from products.models import Product, SolarPackage


class PaymentPlan(models.Model):
    """Payment plan templates for solar packages"""
    
    PAYMENT_TERM_CHOICES = [
        ('once_off', 'Once Off (100% upfront)'),
        ('three_months', '3-Month Installment Plan'),
        ('six_months', '6-Month Installment Plan'),
        ('twelve_months', '12-Month Installment Plan'),
    ]
    
    name = models.CharField(max_length=100)
    payment_term = models.CharField(max_length=20, choices=PAYMENT_TERM_CHOICES)
    description = models.TextField(blank=True)
    
    # Installment details
    number_of_installments = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of payment installments"
    )
    installment_interval_days = models.IntegerField(
        default=0,
        help_text="Days between installments (0 for once-off)"
    )
    
    # Fees and interest
    deposit_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Deposit required as percentage of total"
    )
    interest_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Annual interest rate on installments"
    )
    administration_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="One-time administration fee"
    )
    
    # Applicability
    applicable_packages = models.ManyToManyField(
        SolarPackage,
        blank=True,
        related_name='payment_plans',
        help_text="Packages this payment plan applies to (leave empty for all)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'payment_term']
        verbose_name = 'Payment Plan'
        verbose_name_plural = 'Payment Plans'
    
    def __str__(self):
        return f"{self.name} ({self.get_payment_term_display()})"
    
    def calculate_installment_amount(self, total_amount):
        """Calculate per-installment amount including interest"""
        if self.number_of_installments == 1:
            return total_amount
        
        # Simple interest calculation
        annual_rate = self.interest_rate_percent / 100
        monthly_rate = annual_rate / 12
        
        # Amount after adding interest
        total_with_interest = total_amount * (1 + (annual_rate * (self.number_of_installments / 12)))
        
        # Per-installment amount
        return total_with_interest / self.number_of_installments


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
    
    # Payment plan
    payment_plan = models.ForeignKey(PaymentPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotes')
    
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
    
    # Payment plan
    payment_plan = models.ForeignKey(PaymentPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
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


class PaymentSchedule(models.Model):
    """Individual payment schedule for installment plans"""
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('due', 'Due'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_schedule')
    payment_number = models.IntegerField(help_text="Payment sequence number (1, 2, 3...)")
    
    # Amount
    due_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Dates
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['payment_number']
        unique_together = ['order', 'payment_number']
        verbose_name = 'Payment Schedule'
        verbose_name_plural = 'Payment Schedules'
    
    def __str__(self):
        return f"Payment {self.payment_number} - {self.order.order_number} ({self.get_status_display()})"
    
    @property
    def balance_due(self):
        return self.due_amount - self.paid_amount
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.status in ['pending', 'due'] and self.due_date < timezone.now().date()
