"""
Product models for Sungrip Solar equipment
"""
from django.db import models
from django.core.validators import MinValueValidator


class ProductCategory(models.Model):
    """Categories for solar equipment"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Solar equipment products"""
    
    PRODUCT_TYPE_CHOICES = [
        ('solar_panel', 'Solar Panel'),
        ('inverter', 'Inverter'),
        ('battery', 'Battery'),
        ('charge_controller', 'Charge Controller'),
        ('mounting', 'Mounting Equipment'),
        ('cable', 'Cables & Wiring'),
        ('accessory', 'Accessory'),
        ('service', 'Service/Labor'),
    ]
    
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, related_name='products')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES)
    
    # Basic information
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit")
    
    # Description
    short_description = models.TextField(max_length=500, blank=True)
    full_description = models.TextField(blank=True)
    
    # Specifications (JSON field for flexibility)
    specifications = models.JSONField(default=dict, blank=True, help_text="Technical specifications")
    
    # Pricing
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='USD')
    
    # Inventory
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=10)
    unit_of_measure = models.CharField(max_length=20, default='unit')
    
    # Images
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    image_url = models.URLField(blank=True)
    
    # Warranty
    warranty_period_months = models.IntegerField(default=12, help_text="Warranty period in months")
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold
    
    @property
    def profit_margin(self):
        if self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return 0


class SolarPackage(models.Model):
    """Pre-configured solar system packages"""
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Images
    image = models.ImageField(upload_to='solar_packages/', null=True, blank=True)
    image_url = models.URLField(blank=True, help_text="External image URL (if no image uploaded)")
    
    # System sizing
    system_size_kw = models.DecimalField(max_digits=6, decimal_places=2, help_text="System size in kW")
    recommended_for = models.CharField(
        max_length=20,
        choices=[
            ('small_home', 'Small Home (1-2 bedrooms)'),
            ('medium_home', 'Medium Home (3-4 bedrooms)'),
            ('large_home', 'Large Home (5+ bedrooms)'),
            ('small_business', 'Small Business'),
            ('commercial', 'Commercial'),
        ]
    )
    
    # Pricing
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    installation_included = models.BooleanField(default=True)
    
    # Products included (many-to-many with quantities)
    products = models.ManyToManyField(Product, through='PackageItem', related_name='packages')
    
    # Features
    features = models.JSONField(default=list, help_text="List of package features")
    
    # Status
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'system_size_kw']
        verbose_name = 'Solar Package'
        verbose_name_plural = 'Solar Packages'
    
    def __str__(self):
        return f"{self.name} ({self.system_size_kw}kW)"


class PackageItem(models.Model):
    """Products included in a solar package"""
    
    package = models.ForeignKey(SolarPackage, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    notes = models.CharField(max_length=255, blank=True)
    
    class Meta:
        unique_together = ['package', 'product']
        verbose_name = 'Package Item'
        verbose_name_plural = 'Package Items'
    
    def __str__(self):
        return f"{self.package.name} - {self.product.name} (x{self.quantity})"

