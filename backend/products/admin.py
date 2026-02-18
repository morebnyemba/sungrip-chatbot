from django.contrib import admin
from .models import ProductCategory, Product, SolarPackage, PackageItem


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
    list_display = ('name', 'product_type', 'brand', 'sku', 'selling_price', 'stock_quantity', 'is_active')
    list_filter = ('product_type', 'category', 'is_active', 'is_featured')
    search_fields = ('name', 'brand', 'sku', 'model_number')
    list_editable = ('selling_price', 'is_active')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SolarPackage)
class SolarPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'system_size_kw', 'recommended_for', 'total_price', 'is_active', 'is_popular', 'display_order')
    list_filter = ('recommended_for', 'is_active', 'is_popular', 'installation_included')
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
        ('Pricing', {
            'fields': ('total_price', 'installation_included')
        }),
        ('Features & Status', {
            'fields': ('features', 'is_active', 'is_popular', 'display_order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
