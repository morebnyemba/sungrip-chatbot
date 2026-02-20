from django.contrib import admin
from .models import ProductCategory, Product, ProductImage, SolarPackage, PackageItem


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'display_order')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('display_order', 'is_active')


class PackageItemInline(admin.TabularInline):
    model = PackageItem
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type', 'brand', 'sku', 'selling_price', 'stock_quantity', 'is_active', 'whatsapp_catalog_id')
    list_filter = ('product_type', 'category', 'is_active', 'is_featured')
    search_fields = ('name', 'brand', 'sku', 'model_number')
    list_editable = ('selling_price', 'is_active')
    readonly_fields = ('created_at', 'updated_at', 'whatsapp_catalog_id', 'meta_sync_attempts', 'meta_sync_last_error', 'meta_sync_last_attempt', 'meta_sync_last_success')
    inlines = [ProductImageInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'product_type', 'brand', 'model_number', 'sku')
        }),
        ('Description', {
            'fields': ('short_description', 'full_description', 'specifications')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'selling_price', 'currency')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold', 'unit_of_measure')
        }),
        ('Images', {
            'fields': ('image', 'image_url')
        }),
        ('Warranty', {
            'fields': ('warranty_period_months',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Meta Catalog Sync', {
            'fields': ('whatsapp_catalog_id', 'meta_sync_attempts', 'meta_sync_last_error', 'meta_sync_last_attempt', 'meta_sync_last_success'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['reset_meta_sync', 'sync_to_meta_catalog']

    @admin.action(description="Reset Meta sync attempts (allow retry)")
    def reset_meta_sync(self, request, queryset):
        for product in queryset:
            product.reset_meta_sync_attempts()
        self.message_user(request, f"Reset sync attempts for {queryset.count()} product(s).")

    @admin.action(description="Sync selected products to Meta Catalog")
    def sync_to_meta_catalog(self, request, queryset):
        from meta_integration.catalog_service import MetaCatalogService
        service = MetaCatalogService()
        success = 0
        for product in queryset.filter(is_active=True, sku__isnull=False):
            try:
                service.sync_product_update(product)
                success += 1
            except Exception as exc:
                self.message_user(request, f"Error syncing {product.name}: {exc}", level='error')
        self.message_user(request, f"Successfully synced {success} product(s) to Meta Catalog.")


@admin.register(SolarPackage)
class SolarPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'system_size_kw', 'recommended_for', 'total_price', 'payment_type', 'installment_months', 'is_active', 'is_popular', 'display_order')
    list_filter = ('recommended_for', 'payment_type', 'is_active', 'is_popular', 'installation_included')
    search_fields = ('name', 'description')
    list_editable = ('total_price', 'is_active', 'is_popular', 'display_order')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PackageItemInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'image', 'image_url')
        }),
        ('System Details', {
            'fields': ('system_size_kw', 'recommended_for')
        }),
        ('Pricing & Payment', {
            'fields': ('total_price', 'payment_type', 'installment_months', 'installation_included')
        }),
        ('Equipment & Powers', {
            'fields': ('equipment_summary', 'powers')
        }),
        ('Features & Status', {
            'fields': ('features', 'is_active', 'is_popular', 'display_order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
