# backend/flows/actions.py

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class FlowActionRegistry:
    """
    A central registry for custom flow actions. This makes actions discoverable
    and prevents issues with circular imports or app loading order.
    """
    def __init__(self):
        self._actions = {}

    def register(self, name, func):
        self._actions[name] = func
        logger.info(f"Registered flow action: '{name}'")

    def get(self, name):
        return self._actions.get(name)


# Instantiate the registry
flow_action_registry = FlowActionRegistry()


def register_flow_action(name):
    """A decorator to register a flow action function."""
    def decorator(func):
        flow_action_registry.register(name, func)
        return func
    return decorator


@register_flow_action('map_wa_response')
def map_wa_response(contact, context: dict, params: dict) -> dict:
    """
    Maps WhatsApp Flow response variable names to the names expected
    by the conversational flow.  Also copies contact_name → customer_name
    when ensure_customer_profile hasn't already set it.

    Expected params:
        - mappings: dict of {wa_field: flow_field}
                    e.g. {"address": "installation_address"}
    """
    mappings = params.get('mappings', {})
    mapped = 0
    for wa_key, flow_key in mappings.items():
        if wa_key in context and flow_key not in context:
            context[flow_key] = context[wa_key]
            mapped += 1
    logger.info(f"map_wa_response: mapped {mapped}/{len(mappings)} field(s)")
    return context


@register_flow_action('ensure_customer_profile')
def ensure_customer_profile(contact, context: dict, params: dict) -> dict:
    """
    Ensures a customer profile exists for the contact.
    Creates one from the WhatsApp profile name if not found.
    Sets context variables: customer_name, customer_exists.
    """
    from customers.models import Customer

    try:
        profile_name = getattr(contact, 'profile_name', '') or ''
        phone = getattr(contact, 'phone_number', '') or ''

        customer, created = Customer.objects.get_or_create(
            phone_number=phone,
            defaults={
                'full_name': profile_name or 'WhatsApp User',
                'whatsapp_number': phone,
            }
        )

        # Update profile name if it was missing
        if not created and not customer.full_name and profile_name:
            customer.full_name = profile_name
            customer.save(update_fields=['full_name'])

        context['customer_name'] = customer.full_name
        context['customer_exists'] = not created
        logger.info(
            f"ensure_customer_profile: {'found' if not created else 'created'} "
            f"customer '{customer.full_name}' for {phone}"
        )
    except Exception as e:
        logger.error(f"ensure_customer_profile error: {e}", exc_info=True)
        context['customer_name'] = getattr(contact, 'profile_name', 'Customer')
        context['customer_exists'] = False

    return context


@register_flow_action('calculate_solar_quote')
def calculate_solar_quote(contact, context: dict, params: dict) -> dict:
    """
    Calculates a solar system quote based on customer information.
    
    Expected params:
        - save_to_variable: Variable name to save result (default: 'solar_quote')
    
    Uses context variables:
        - monthly_bill: Customer's average monthly electricity bill
    """
    save_to_var = params.get('save_to_variable', 'solar_quote')
    
    try:
        monthly_bill = float(context.get('monthly_bill', 0))
        
        if monthly_bill <= 0:
            logger.warning(f"calculate_solar_quote: Invalid monthly bill amount: {monthly_bill}")
            context[save_to_var] = {
                'success': False,
                'message': 'Invalid monthly bill amount'
            }
            return context
        
        # Simple calculation: 1kW for every $100-150 of monthly bill
        # Average cost per watt: ~$2-3
        system_size_kw = monthly_bill / 120  # Rough estimate based on average usage
        system_cost = system_size_kw * 2500  # ~$2500 per kW installed
        
        # ROI assumption: 5-7 year payback period
        roi_months = (system_cost / monthly_bill) * 12
        
        quote = {
            'success': True,
            'monthly_bill': monthly_bill,
            'estimated_system_size_kw': round(system_size_kw, 2),
            'estimated_cost': round(system_cost, 2),
            'estimated_roi_months': round(roi_months, 0),
            'timestamp': timezone.now().isoformat()
        }
        
        context[save_to_var] = quote
        logger.info(f"Successfully calculated solar quote: {quote}")
        
    except Exception as e:
        logger.error(f"Error calculating solar quote: {e}", exc_info=True)
        context[save_to_var] = {
            'success': False,
            'message': f'Error calculating quote: {str(e)}'
        }
    
    return context


@register_flow_action('log_context_data')
def log_context_data(contact, context: dict, params: dict) -> dict:
    """
    Logs all relevant context data for debugging.
    
    Expected params:
        - log_keys: List of keys to log (optional, logs all if not provided)
    """
    log_keys = params.get('log_keys')
    
    if log_keys:
        for key in log_keys:
            value = context.get(key)
            logger.info(f"Context [{key}]: {value}")
    else:
        logger.info(f"Full context data: {context}")
    
    return context


@register_flow_action('save_quote_request')
def save_quote_request(contact, context: dict, params: dict) -> dict:
    """
    Saves quote request information for follow-up by sales team.
    
    Expected params:
        - save_to_variable: Variable name to save result (default: 'quote_request_saved')
    
    Uses context variables:
        - monthly_bill: Customer's monthly bill
        - roof_type: Type of roof
        - location: Customer location
    """
    from orders.models import QuoteRequest
    from customers.models import Customer
    
    save_to_var = params.get('save_to_variable', 'quote_request_saved')
    
    try:
        # Generate unique request ID
        request_id = f"QUOTE-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        # Extract data from context
        monthly_bill = context.get('monthly_bill')
        roof_type = context.get('roof_type')
        location = context.get('location')
        customer_name = getattr(contact, 'profile_name', None) or getattr(contact, 'name', 'Unknown') if contact else 'Unknown'
        
        # Try to find or create customer
        customer = None
        if contact and hasattr(contact, 'customer'):
            customer = contact.customer
        
        # Create QuoteRequest in database
        quote_request_obj = QuoteRequest.objects.create(
            customer=customer,
            contact=contact,
            request_id=request_id,
            customer_name=customer_name,
            monthly_bill=monthly_bill,
            roof_type=roof_type,
            location=location,
            status='pending'
        )
        
        quote_request = {
            'success': True,
            'id': quote_request_obj.id,
            'request_id': request_id,
            'monthly_bill': monthly_bill,
            'roof_type': roof_type,
            'location': location,
            'customer_name': customer_name,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Quote request saved to database: {quote_request}")
        
        context[save_to_var] = quote_request
        
    except Exception as e:
        logger.error(f"Error saving quote request: {e}", exc_info=True)
        context[save_to_var] = {
            'success': False,
            'message': f'Error saving quote request: {str(e)}'
        }
    
    return context


@register_flow_action('update_context_variable')
def update_context_variable(contact, context: dict, params: dict) -> dict:
    """
    Generic action to update context variables with computed values.
    
    Expected params:
        - variable_name: Name of the variable to set
        - variable_value: Value to set (can be a string with template variables)
    """
    variable_name = params.get('variable_name')
    variable_value = params.get('variable_value')
    
    if not variable_name:
        logger.error("update_context_variable: 'variable_name' not provided in params")
        return context
    
    try:
        # Basic template variable replacement
        if isinstance(variable_value, str):
            # Replace template variables like {{monthly_bill}}
            for key, value in context.items():
                placeholder = f"{{{{{key}}}}}"
                variable_value = variable_value.replace(placeholder, str(value))
        
        context[variable_name] = variable_value
        logger.info(f"Updated context variable '{variable_name}' = {variable_value}")
        
    except Exception as e:
        logger.error(f"Error updating context variable: {e}", exc_info=True)
    
    return context


@register_flow_action('check_whatsapp_flow')
def check_whatsapp_flow(contact, context: dict, params: dict) -> dict:
    """
    Checks if a published WhatsApp interactive flow exists.
    
    Expected params:
        - flow_name: Name of the WhatsApp flow to check
        - save_to_variable: Variable name to save flow data (default: 'wa_flow_data')
    
    Sets the variable to flow data dict if found, or does not set it if not found.
    The flow definition can then use 'variable_exists' condition to branch.
    """
    from flows.models import WhatsAppFlow

    flow_name = params.get('flow_name')
    save_to_var = params.get('save_to_variable', 'wa_flow_data')

    if not flow_name:
        logger.error("check_whatsapp_flow: 'flow_name' not provided in params")
        return context

    try:
        wa_flow = WhatsAppFlow.objects.filter(
            name=flow_name,
            sync_status='published'
        ).first()

        if wa_flow and wa_flow.flow_id:
            context[save_to_var] = {
                'flow_id': wa_flow.flow_id,
                'friendly_name': wa_flow.friendly_name,
                'name': wa_flow.name,
            }
            logger.info(f"Found published WhatsApp flow '{flow_name}' with ID {wa_flow.flow_id}")
        else:
            logger.info(f"No published WhatsApp flow found for '{flow_name}'")

    except Exception as e:
        logger.error(f"Error checking WhatsApp flow '{flow_name}': {e}", exc_info=True)

    return context


@register_flow_action('fetch_solar_packages')
def fetch_solar_packages(contact, context: dict, params: dict) -> dict:
    """
    Fetches active solar packages from the database and formats them for display.

    Expected params:
        - save_to_variable: Variable name to save the formatted text
                            (default: 'packages_text')

    Sets context variables:
        - <save_to_variable>: Formatted multi-line package listing
        - packages_count: Number of active packages found
    """
    from products.models import SolarPackage

    save_to_var = params.get('save_to_variable', 'packages_text')

    try:
        packages = SolarPackage.objects.filter(is_active=True).order_by('display_order', 'system_size_kw')

        if not packages.exists():
            context[save_to_var] = (
                "We're currently updating our package offerings. "
                "Please contact our team for the latest pricing."
            )
            context['packages_count'] = 0
            logger.info("fetch_solar_packages: No active packages found in database")
            return context

        lines = ["☀️ *Sungrip Solar Packages* ☀️\n"]
        for pkg in packages:
            popular_badge = " ⭐ POPULAR" if pkg.is_popular else ""
            recommended = pkg.get_recommended_for_display()
            lines.append(
                f"📦 *{pkg.name.upper()}*{popular_badge}\n"
                f"• {pkg.system_size_kw}kW Solar System\n"
                f"• Recommended for: {recommended}\n"
            )

            # Add features from JSON field
            if pkg.features:
                for feature in pkg.features:
                    lines.append(f"• {feature}")

            if pkg.installation_included:
                lines.append("• Installation Included")

            lines.append(f"💰 Price: ${pkg.total_price:,.0f}\n")

        context[save_to_var] = "\n".join(lines)
        context['packages_count'] = packages.count()
        logger.info(f"fetch_solar_packages: Loaded {packages.count()} packages from database")

    except Exception as e:
        logger.error(f"fetch_solar_packages error: {e}", exc_info=True)
        context[save_to_var] = (
            "Sorry, we could not load our packages right now. "
            "Please try again later or contact support."
        )
        context['packages_count'] = 0

    return context


@register_flow_action('build_packages_interactive_list')
def build_packages_interactive_list(contact, context: dict, params: dict) -> dict:
    """
    Queries active SolarPackages from the DB and builds a WhatsApp interactive
    list message payload grouped by payment type, storing it in a context
    variable so the flow engine's ``send_dynamic_message`` action type can
    dispatch it.

    Sets context variables:
        - _packages_list_msg: Complete interactive list message config
        - _package_id_map: Dict mapping interactive row IDs to package PKs
        - packages_count: Number of packages found
    """
    from products.models import SolarPackage

    try:
        packages = SolarPackage.objects.filter(is_active=True).order_by(
            'display_order', 'system_size_kw'
        )

        if not packages.exists():
            context['_packages_list_msg'] = {
                'message_type': 'text',
                'text': {
                    'body': (
                        "We're currently updating our package offerings.\n"
                        "Please contact our team for the latest pricing.\n\n"
                        "Type 'menu' to return to the main menu."
                    )
                }
            }
            context['packages_count'] = 0
            context['_package_id_map'] = {}
            return context

        # Group packages by payment type + installment duration
        # WhatsApp allows max 10 rows total across all sections
        cash_rows = []
        plan_3mo_rows = []
        plan_6mo_rows = []
        id_map = {}
        total_rows = 0
        MAX_ROWS = 10

        for pkg in packages:
            if total_rows >= MAX_ROWS:
                break

            row_id = f"pkg_{pkg.pk}"
            popular = " ⭐" if pkg.is_popular else ""

            # Build title — WhatsApp max is 24 chars
            title = f"{pkg.name}{popular}"
            if len(title) > 24:
                max_name = 24 - len(popular)
                title = f"{pkg.name[:max_name]}{popular}"

            # Build description — WhatsApp max is 72 chars
            if pkg.payment_type == 'installment' and pkg.installment_months:
                if pkg.deposit_amount:
                    remaining = pkg.total_price - pkg.deposit_amount
                    num_payments = pkg.installment_months - 1
                    installment = remaining / num_payments if num_payments else remaining
                    desc = (
                        f"{pkg.system_size_kw}kW · ${pkg.deposit_amount:,.0f} dep "
                        f"+ ${installment:,.0f}×{num_payments}"
                    )
                else:
                    monthly = pkg.total_price / pkg.installment_months
                    desc = f"{pkg.system_size_kw}kW · ${pkg.total_price:,.0f} (${monthly:,.0f}/mo)"
            else:
                desc = f"{pkg.system_size_kw}kW · ${pkg.total_price:,.0f}"

            row = {
                "id": row_id,
                "title": title,
                "description": desc[:72]
            }
            id_map[row_id] = pkg.pk
            total_rows += 1

            if pkg.payment_type == 'installment' and pkg.installment_months == 3:
                plan_3mo_rows.append(row)
            elif pkg.payment_type == 'installment':
                plan_6mo_rows.append(row)
            else:
                cash_rows.append(row)

        if packages.count() > MAX_ROWS:
            logger.warning(
                "Active packages (%d) exceed WhatsApp max rows (%d). "
                "Only first %d shown. Deactivate some packages in admin.",
                packages.count(), MAX_ROWS, MAX_ROWS
            )

        sections = []
        if cash_rows:
            sections.append({
                'title': '💵 Cash on Delivery',
                'rows': cash_rows
            })
        if plan_3mo_rows:
            sections.append({
                'title': '🔥 3-Month Payment Plan',
                'rows': plan_3mo_rows
            })
        if plan_6mo_rows:
            sections.append({
                'title': '📆 6-Month Payment Plan',
                'rows': plan_6mo_rows
            })

        context['_packages_list_msg'] = {
            'message_type': 'interactive',
            'interactive': {
                'type': 'list',
                'header': {'type': 'text', 'text': '☀️ Sungrip Solar Packages'},
                'body': {
                    'text': (
                        "Browse our solar energy packages below.\n\n"
                        "💵 *Cash* — pay on delivery & installation\n"
                        "� *3-Month Plan* — short-term credit\n"
                        "�📆 *6-Month Plan* — spread the cost\n\n"
                        "Each package includes panels, inverter, battery "
                        "& professional installation.\n\n"
                        "Tap a package for full details 👇"
                    )
                },
                'footer': {'text': 'Prices in USD · Supply & Fix included'},
                'action': {
                    'button': '📦 View Packages',
                    'sections': sections
                }
            }
        }
        context['_package_id_map'] = id_map
        context['packages_count'] = packages.count()
        logger.info(
            f"build_packages_interactive_list: Built list with "
            f"{packages.count()} packages in {len(sections)} sections"
        )

    except Exception as e:
        logger.error(
            f"build_packages_interactive_list error: {e}", exc_info=True
        )
        context['_packages_list_msg'] = {
            'message_type': 'text',
            'text': {
                'body': (
                    "Sorry, we could not load our packages right now.\n"
                    "Please try again later or type 'menu'."
                )
            }
        }
        context['_package_id_map'] = {}
        context['packages_count'] = 0

    return context


@register_flow_action('fetch_package_details')
def fetch_package_details(contact, context: dict, params: dict) -> dict:
    """
    Looks up a single SolarPackage by the interactive list selection and
    formats its full details for display.

    Expected params:
        - selection_variable: Context variable holding the selected row ID
                              (default: 'selected_package')

    Uses context variables:
        - _package_id_map: Mapping of row IDs → PKs (set by build_packages_interactive_list)

    Sets context variables:
        - package_name: Package name
        - package_detail_text: Formatted detail text for display
        - package_found: Boolean indicating whether the package was found
    """
    from products.models import SolarPackage

    selection_var = params.get('selection_variable', 'selected_package')
    selected_id = context.get(selection_var, '')
    id_map = context.get('_package_id_map', {})

    try:
        pkg_pk = id_map.get(selected_id)
        if not pkg_pk:
            context['package_found'] = False
            context['package_detail_text'] = (
                "Sorry, I couldn't find that package. "
                "Please select one from the list."
            )
            return context

        pkg = SolarPackage.objects.get(pk=pkg_pk, is_active=True)

        lines = [
            f"📦 *{pkg.name.upper()}*",
        ]
        if pkg.is_popular:
            lines.append("⭐ MOST POPULAR")

        lines.append("")
        lines.append(f"⚡ *System Size:* {pkg.system_size_kw} kW")
        lines.append(f"🏠 *Recommended for:* {pkg.get_recommended_for_display()}")

        # ── Pricing & payment info ──
        lines.append(f"💰 *Total Price:* ${pkg.total_price:,.0f} USD")
        if pkg.payment_type == 'installment' and pkg.installment_months:
            if pkg.deposit_amount:
                remaining = pkg.total_price - pkg.deposit_amount
                num_payments = pkg.installment_months - 1
                installment = remaining / num_payments if num_payments else remaining
                lines.append(
                    f"💳 *Deposit:* ${pkg.deposit_amount:,.0f}"
                )
                lines.append(
                    f"📆 *Then:* ${installment:,.0f}/month × {num_payments} months"
                )
            else:
                monthly = pkg.total_price / pkg.installment_months
                lines.append(f"📆 *Payment Plan:* {pkg.installment_months} months × ${monthly:,.0f}/mo")
        else:
            lines.append("💵 *Payment:* Cash on delivery & installation")
        lines.append("")

        # ── Equipment list (from JSON field first, then M2M fallback) ──
        if getattr(pkg, 'equipment_summary', None) and pkg.equipment_summary:
            lines.append("🔧 *Equipment Included:*")
            for item in pkg.equipment_summary:
                lines.append(f"  • {item}")
            lines.append("")
        else:
            package_items = pkg.packageitem_set.select_related('product').all()
            if package_items.exists():
                lines.append("🔧 *Equipment Included:*")
                for item in package_items:
                    lines.append(f"  • {item.quantity}x {item.product.name}")
                lines.append("")

        # ── What it powers ──
        if getattr(pkg, 'powers', None) and pkg.powers:
            lines.append("🔌 *System Powers:*")
            for load in pkg.powers:
                lines.append(f"  ⚡ {load}")
            lines.append("")

        if pkg.installation_included:
            lines.append("✅ Professional supply & installation included")
            lines.append("ℹ️ Outside Harare — transport charges may apply")

        # ── Features ──
        if pkg.features:
            lines.append("")
            lines.append("*Key Benefits:*")
            for feature in pkg.features:
                lines.append(f"  ✓ {feature}")

        # ── Description ──
        if pkg.description:
            lines.append("")
            lines.append(f"_{pkg.description}_")

        # ── Contact ──
        lines.append("")
        lines.append("📞 WhatsApp: 0782 233 111 / 0777 139 159")

        context['package_name'] = pkg.name
        context['package_detail_text'] = "\n".join(lines)
        context['package_found'] = True
        context['package_price'] = f"${pkg.total_price:,.0f} USD"
        context['package_system_size'] = f"{pkg.system_size_kw} kW"

        # Map system_size_kw → raw interactive ID used by LABEL_MAPS
        kw_to_id = {3.5: '3.5kva', 4.2: '4.2kva', 6.2: '6.2kva'}
        context['system_size'] = kw_to_id.get(
            float(pkg.system_size_kw), f"{pkg.system_size_kw}kva"
        )

        # Map payment_type → raw interactive ID used by LABEL_MAPS
        if pkg.payment_type == 'installment' and pkg.installment_months:
            if pkg.deposit_amount:
                remaining = pkg.total_price - pkg.deposit_amount
                num_payments = pkg.installment_months - 1
                installment = remaining / num_payments if num_payments else remaining
                context['package_payment_label'] = (
                    f"💳 ${pkg.deposit_amount:,.0f} deposit + "
                    f"${installment:,.0f}/mo × {num_payments}"
                )
            else:
                monthly = pkg.total_price / pkg.installment_months
                context['package_payment_label'] = (
                    f"📆 {pkg.installment_months}-Month Plan (${monthly:,.0f}/mo)"
                )
            context['payment_preference'] = f"installment_{pkg.installment_months}"
        else:
            context['package_payment_label'] = "💵 Cash on Delivery"
            context['payment_preference'] = 'cash'

        logger.info(f"fetch_package_details: Loaded details for '{pkg.name}'")

    except SolarPackage.DoesNotExist:
        context['package_found'] = False
        context['package_detail_text'] = (
            "Sorry, that package is no longer available. "
            "Please select another from the list."
        )
    except Exception as e:
        logger.error(f"fetch_package_details error: {e}", exc_info=True)
        context['package_found'] = False
        context['package_detail_text'] = (
            "Sorry, something went wrong loading package details. "
            "Please try again."
        )

    return context


# ---------------------------------------------------------------------------
# Label formatting action
# ---------------------------------------------------------------------------

# Maps raw interactive IDs to human-friendly display labels.
# Used before confirmation steps so summaries read naturally.
LABEL_MAPS = {
    'payment_preference': {
        'cash': '💵 Cash / Full Payment',
        'installment_3': '🔥 3-Month Payment Plan',
        'installment_6': '📆 6-Month Payment Plan',
    },
    'system_size': {
        '3.5kva': '⚡ 3.5 kVA System',
        '4.2kva': '⚡ 4.2 kVA System',
        '6.2kva': '⚡ 6.2 kVA System',
        'not_sure': '🤔 Not Sure Yet',
    },
    'time_preference': {
        'morning': '🌅 Morning (8 AM – 12 PM)',
        'afternoon': '🌇 Afternoon (12 PM – 5 PM)',
    },
    'roof_type': {
        'tile': '🏠 Tile Roof',
        'metal': '🏠 Metal / IBR',
        'asbestos': '🏠 Asbestos',
        'concrete': '🏠 Flat Concrete',
        'other': '🏠 Other',
    },
    'property_type': {
        'residential': '🏠 Residential',
        'commercial': '🏢 Commercial',
        'industrial': '🏭 Industrial',
    },
    'support_category': {
        'technical': '🔧 Technical Issues',
        'billing': '💳 Billing & Payments',
        'installation': '🏗️ Installation Support',
        'product_info': '📦 Product Information',
        'other': '📝 Other',
    },
    'contact_method': {
        'whatsapp': '💬 WhatsApp',
        'phone_call': '📞 Phone Call',
        'email': '📧 Email',
    },
}


@register_flow_action('format_labels')
def format_labels(contact, context: dict, params: dict) -> dict:
    """
    Converts raw interactive IDs to human-readable labels for
    confirmation/summary messages.

    Expected params:
        - variables: list of context variable names to format
                     (default: all known label maps)

    For each variable, creates a '_display' suffixed version:
        e.g. payment_preference='cash' → payment_preference_display='💵 Cash / Full Payment'

    Also overwrites the original variable so {{payment_preference}}
    renders the friendly label directly in templates.
    """
    variables = params.get('variables', list(LABEL_MAPS.keys()))

    for var_name in variables:
        raw_value = context.get(var_name, '')
        label_map = LABEL_MAPS.get(var_name, {})
        display_value = label_map.get(str(raw_value), str(raw_value))

        # Store both the display version and overwrite the original
        context[f'{var_name}_display'] = display_value
        context[var_name] = display_value

    logger.info(f"format_labels: Formatted {len(variables)} variable(s)")
    return context


# ---------------------------------------------------------------------------
# Product Catalog actions (following hanna pattern)
# ---------------------------------------------------------------------------

@register_flow_action('build_product_categories_list')
def build_product_categories_list(contact, context: dict, params: dict) -> dict:
    """
    Builds a WhatsApp interactive list of active product categories.

    Sets context variables:
        - _categories_list_msg: Complete interactive list message config
        - _category_id_map: Dict mapping interactive row IDs to category PKs
        - categories_count: Number of categories found
    """
    from products.models import ProductCategory, Product

    try:
        # Only show categories that actually have active products
        categories = (
            ProductCategory.objects
            .filter(is_active=True)
            .order_by('display_order', 'name')
        )

        # Filter to categories with at least one active product
        categories_with_products = []
        for cat in categories:
            product_count = Product.objects.filter(
                category=cat, is_active=True
            ).count()
            if product_count > 0:
                categories_with_products.append((cat, product_count))

        if not categories_with_products:
            context['_categories_list_msg'] = {
                'message_type': 'text',
                'text': {
                    'body': (
                        "We're currently updating our product catalog.\n"
                        "Please check back soon or contact our team.\n\n"
                        "Type 'menu' to return to the main menu."
                    ),
                },
            }
            context['categories_count'] = 0
            context['_category_id_map'] = {}
            return context

        MAX_ROWS = 10
        rows = []
        id_map = {}

        for cat, count in categories_with_products[:MAX_ROWS]:
            row_id = f"cat_{cat.pk}"
            icon = cat.icon + " " if cat.icon else ""

            title = f"{icon}{cat.name}"
            if len(title) > 24:
                title = title[:24]

            desc = f"{count} product{'s' if count != 1 else ''} available"
            if cat.description:
                desc = cat.description[:72]

            rows.append({
                "id": row_id,
                "title": title,
                "description": desc[:72],
            })
            id_map[row_id] = cat.pk

        context['_categories_list_msg'] = {
            'message_type': 'interactive',
            'interactive': {
                'type': 'list',
                'header': {'type': 'text', 'text': '🛒 Product Categories'},
                'body': {
                    'text': (
                        "Browse our solar equipment catalog.\n\n"
                        "We stock panels, inverters, batteries, "
                        "charge controllers, cables & accessories.\n\n"
                        "Select a category to see available products 👇"
                    ),
                },
                'footer': {'text': 'Prices in USD'},
                'action': {
                    'button': '📂 Browse Categories',
                    'sections': [{
                        'title': 'Categories',
                        'rows': rows,
                    }],
                },
            },
        }
        context['_category_id_map'] = id_map
        context['categories_count'] = len(categories_with_products)
        logger.info(
            f"build_product_categories_list: {len(categories_with_products)} categories"
        )

    except Exception as exc:
        logger.error(f"build_product_categories_list error: {exc}", exc_info=True)
        context['_categories_list_msg'] = {
            'message_type': 'text',
            'text': {
                'body': (
                    "Sorry, we could not load our product catalog right now.\n"
                    "Please try again later or type 'menu'."
                ),
            },
        }
        context['_category_id_map'] = {}
        context['categories_count'] = 0

    return context


@register_flow_action('build_products_interactive_list')
def build_products_interactive_list(contact, context: dict, params: dict) -> dict:
    """
    Queries active Products for a selected category and builds a WhatsApp
    interactive list message.

    Expected params:
        - category_variable: Context variable holding the selected category row ID
                             (default: 'selected_category')

    Sets context variables:
        - _products_list_msg: Complete interactive list message config
        - _product_id_map: Dict mapping row IDs to product PKs
        - products_count: Number of products found
        - selected_category_name: Name of the selected category
    """
    from products.models import Product, ProductCategory

    cat_var = params.get('category_variable', 'selected_category')
    selected_id = context.get(cat_var, '')
    id_map_cat = context.get('_category_id_map', {})

    try:
        cat_pk = id_map_cat.get(selected_id)
        if not cat_pk:
            # Fallback: show all active products
            products = Product.objects.filter(is_active=True).order_by('name')
            cat_name = "All Products"
        else:
            category = ProductCategory.objects.get(pk=cat_pk, is_active=True)
            cat_name = category.name
            products = Product.objects.filter(
                category=category, is_active=True
            ).order_by('name')

        context['selected_category_name'] = cat_name

        if not products.exists():
            context['_products_list_msg'] = {
                'message_type': 'text',
                'text': {
                    'body': (
                        f"No products available in *{cat_name}* right now.\n"
                        "Please try another category or type 'menu'."
                    ),
                },
            }
            context['_product_id_map'] = {}
            context['products_count'] = 0
            return context

        MAX_ROWS = 10
        rows = []
        prod_id_map = {}

        for product in products[:MAX_ROWS]:
            row_id = f"prod_{product.pk}"

            title = product.name
            if len(title) > 24:
                title = title[:24]

            # Build description: brand + price + stock status
            parts = []
            if product.brand:
                parts.append(product.brand)
            parts.append(f"${product.selling_price:,.0f}")
            if product.stock_quantity > 0:
                parts.append("In Stock")
            else:
                parts.append("Out of Stock")
            desc = " · ".join(parts)

            rows.append({
                "id": row_id,
                "title": title,
                "description": desc[:72],
            })
            prod_id_map[row_id] = product.pk

        if products.count() > MAX_ROWS:
            logger.warning(
                f"Category '{cat_name}' has {products.count()} products, "
                f"only showing first {MAX_ROWS}."
            )

        context['_products_list_msg'] = {
            'message_type': 'interactive',
            'interactive': {
                'type': 'list',
                'header': {'type': 'text', 'text': f'🔧 {cat_name}'},
                'body': {
                    'text': (
                        f"Here are our available *{cat_name}* products.\n\n"
                        "Select a product to see full specifications "
                        "and pricing 👇"
                    ),
                },
                'footer': {'text': 'Prices in USD'},
                'action': {
                    'button': '📦 View Products',
                    'sections': [{
                        'title': cat_name,
                        'rows': rows,
                    }],
                },
            },
        }
        context['_product_id_map'] = prod_id_map
        context['products_count'] = products.count()
        logger.info(
            f"build_products_interactive_list: {products.count()} products "
            f"in '{cat_name}'"
        )

    except ProductCategory.DoesNotExist:
        context['_products_list_msg'] = {
            'message_type': 'text',
            'text': {
                'body': (
                    "Sorry, that category is no longer available.\n"
                    "Please select another from the list."
                ),
            },
        }
        context['_product_id_map'] = {}
        context['products_count'] = 0
    except Exception as exc:
        logger.error(
            f"build_products_interactive_list error: {exc}", exc_info=True
        )
        context['_products_list_msg'] = {
            'message_type': 'text',
            'text': {
                'body': (
                    "Sorry, we could not load products right now.\n"
                    "Please try again later or type 'menu'."
                ),
            },
        }
        context['_product_id_map'] = {}
        context['products_count'] = 0

    return context


@register_flow_action('fetch_product_details')
def fetch_product_details(contact, context: dict, params: dict) -> dict:
    """
    Looks up a single Product by the interactive list selection and
    formats its full details (specs, pricing, warranty, stock).

    Expected params:
        - selection_variable: Context variable holding the selected row ID
                              (default: 'selected_product')

    Uses context variables:
        - _product_id_map: Mapping of row IDs → PKs

    Sets context variables:
        - product_name: Product name
        - product_detail_text: Formatted detail text
        - product_price_display: Formatted price string
        - product_found: Boolean
    """
    from products.models import Product

    sel_var = params.get('selection_variable', 'selected_product')
    selected_id = context.get(sel_var, '')
    id_map = context.get('_product_id_map', {})

    try:
        prod_pk = id_map.get(selected_id)
        if not prod_pk:
            context['product_found'] = False
            context['product_detail_text'] = (
                "Sorry, I couldn't find that product. "
                "Please select one from the list."
            )
            return context

        product = Product.objects.get(pk=prod_pk, is_active=True)

        lines = [f"🔧 *{product.name.upper()}*"]
        if product.is_featured:
            lines.append("⭐ FEATURED PRODUCT")
        lines.append("")

        if product.brand:
            lines.append(f"🏷️ *Brand:* {product.brand}")
        if product.model_number:
            lines.append(f"📋 *Model:* {product.model_number}")
        lines.append(f"🔖 *SKU:* {product.sku}")
        if product.category:
            lines.append(f"📂 *Category:* {product.category.name}")
        lines.append("")

        # Pricing
        lines.append(f"💰 *Price:* ${product.selling_price:,.2f} {product.currency}")
        lines.append("")

        # Stock
        if product.stock_quantity > 0:
            lines.append(f"✅ *In Stock:* {product.stock_quantity} {product.unit_of_measure}(s)")
        else:
            lines.append("❌ *Currently Out of Stock*")
        lines.append("")

        # Specifications (JSON field)
        if product.specifications:
            lines.append("📊 *Specifications:*")
            for key, value in product.specifications.items():
                display_key = key.replace('_', ' ').title()
                lines.append(f"  • {display_key}: {value}")
            lines.append("")

        # Description
        if product.short_description:
            lines.append(f"_{product.short_description}_")
            lines.append("")

        # Warranty
        if product.warranty_period_months:
            years = product.warranty_period_months // 12
            months = product.warranty_period_months % 12
            if years and months:
                warranty_text = f"{years} year(s) {months} month(s)"
            elif years:
                warranty_text = f"{years} year(s)"
            else:
                warranty_text = f"{months} month(s)"
            lines.append(f"🛡️ *Warranty:* {warranty_text}")

        lines.append("")
        lines.append("📞 WhatsApp: 0782 233 111 / 0777 139 159")

        context['product_name'] = product.name
        context['product_detail_text'] = "\n".join(lines)
        context['product_found'] = True
        context['product_price_display'] = f"${product.selling_price:,.2f} {product.currency}"
        context['product_sku'] = product.sku
        logger.info(f"fetch_product_details: Loaded '{product.name}'")

    except Product.DoesNotExist:
        context['product_found'] = False
        context['product_detail_text'] = (
            "Sorry, that product is no longer available. "
            "Please select another from the list."
        )
    except Exception as exc:
        logger.error(f"fetch_product_details error: {exc}", exc_info=True)
        context['product_found'] = False
        context['product_detail_text'] = (
            "Sorry, something went wrong loading product details. "
            "Please try again."
        )

    return context


# ---------------------------------------------------------------------------
# Product Order actions
# ---------------------------------------------------------------------------

@register_flow_action('save_product_order')
def save_product_order(contact, context: dict, params: dict) -> dict:
    """
    Creates a ProductOrder record in the database from the catalog flow.

    Uses context variables (set by fetch_product_details + quantity capture):
        - product_name, product_sku, product_price_display
        - _product_id_map, selected_product
        - order_quantity (from quantity capture step, default 1)
        - delivery_method (optional)
        - delivery_address (optional)
        - customer_notes (optional)

    Sets context variables:
        - order_saved: bool
        - order_number: generated reference
        - order_total_display: formatted total price string
    """
    from products.models import Product
    from orders.models import ProductOrder
    from customers.models import Customer

    try:
        # Resolve product
        id_map = context.get('_product_id_map', {})
        selected_id = context.get('selected_product', '')
        prod_pk = id_map.get(selected_id)

        product = None
        if prod_pk:
            try:
                product = Product.objects.get(pk=prod_pk)
            except Product.DoesNotExist:
                pass

        product_name = context.get('product_name', 'Unknown Product')
        product_sku = context.get('product_sku', '')

        # Quantity
        raw_qty = context.get('order_quantity', '1')
        try:
            quantity = max(1, int(float(str(raw_qty))))
        except (ValueError, TypeError):
            quantity = 1

        # Price
        unit_price = 0
        if product:
            unit_price = float(product.selling_price)
        total_price = unit_price * quantity

        # Customer — prefer delivery-form name/phone over defaults
        customer = None
        delivery_name = context.get('delivery_name', '')
        delivery_phone = context.get('delivery_phone', '')
        customer_name = delivery_name or context.get('customer_name', '')
        customer_phone = delivery_phone
        if contact:
            customer_phone = customer_phone or getattr(contact, 'phone_number', '') or ''
            customer_name = customer_name or getattr(contact, 'profile_name', '') or 'WhatsApp User'
            try:
                customer = Customer.objects.filter(phone_number=customer_phone).first()
            except Exception:
                pass

        # Delivery
        delivery_method = context.get('delivery_method', 'not_specified')
        delivery_address = context.get('delivery_address', '')
        customer_notes = context.get('customer_notes', '')

        order = ProductOrder.objects.create(
            customer=customer,
            contact=contact,
            customer_name=customer_name,
            customer_phone=customer_phone,
            product=product,
            product_name=product_name,
            product_sku=product_sku,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            delivery_method=delivery_method,
            delivery_address=delivery_address,
            customer_notes=customer_notes,
            status='pending',
        )

        context['order_saved'] = True
        context['order_number'] = order.order_number
        context['order_total_display'] = f"${total_price:,.2f} USD"
        context['order_quantity'] = str(quantity)
        logger.info(
            f"save_product_order: Created {order.order_number} "
            f"for '{product_name}' x{quantity} = ${total_price:,.2f}"
        )

    except Exception as exc:
        logger.error(f"save_product_order error: {exc}", exc_info=True)
        context['order_saved'] = False
        context['order_number'] = ''
        context['order_total_display'] = ''

    return context


# ---------------------------------------------------------------------------
# Group notification action — mirrors hanna's send_group_notification
# ---------------------------------------------------------------------------

@register_flow_action('send_group_notification')
def send_group_notification(contact, context: dict, params: dict) -> dict:
    """
    Queues notifications to specified Django auth Groups via the
    notifications system.  Mirrors hanna's send_group_notification action.

    Expected params:
        - group_names: list of Django Group name strings
                       e.g. ["Sales Team", "System Admins"]
        - template_name: name of a NotificationTemplate
        - user_ids: (optional) specific User PKs to notify
        - contact_ids: (optional) external Contact PKs to notify
    """
    group_names = params.get('group_names', [])
    template_name = params.get('template_name', '')
    user_ids = params.get('user_ids')
    contact_ids = params.get('contact_ids')

    if not template_name:
        logger.warning("send_group_notification: No template_name provided.")
        return context

    if not group_names and not user_ids and not contact_ids:
        logger.warning("send_group_notification: No recipients specified.")
        return context

    try:
        from notifications.services import queue_notifications_to_users

        queue_notifications_to_users(
            template_name=template_name,
            template_context=context.copy(),
            group_names=group_names or None,
            user_ids=user_ids or None,
            contact_ids=contact_ids or None,
            related_contact=contact,
        )
        logger.info(
            f"send_group_notification: Queued '{template_name}' "
            f"to groups={group_names}"
        )
    except Exception as exc:
        logger.error(
            f"send_group_notification error: {exc}", exc_info=True
        )

    return context


@register_flow_action('save_product_enquiry')
def save_product_enquiry(contact, context: dict, params: dict) -> dict:
    """
    Creates a lightweight ProductOrder with status='pending' to record
    a product enquiry (no quantity commitment yet).

    This ensures every "Enquire" tap from the catalog flow is persisted
    so the sales team has a record to follow up.

    Uses context variables:
        - product_name, product_sku, product_price_display
        - _product_id_map, selected_product

    Sets context variables:
        - enquiry_saved: bool
        - enquiry_reference: generated order reference
    """
    from products.models import Product
    from orders.models import ProductOrder
    from customers.models import Customer

    try:
        id_map = context.get('_product_id_map', {})
        selected_id = context.get('selected_product', '')
        prod_pk = id_map.get(selected_id)

        product = None
        if prod_pk:
            try:
                product = Product.objects.get(pk=prod_pk)
            except Product.DoesNotExist:
                pass

        product_name = context.get('product_name', 'Unknown Product')
        product_sku = context.get('product_sku', '')
        unit_price = float(product.selling_price) if product else 0

        customer = None
        customer_name = context.get('customer_name', '')
        customer_phone = ''
        if contact:
            customer_phone = getattr(contact, 'phone_number', '') or ''
            customer_name = customer_name or getattr(contact, 'profile_name', '') or 'WhatsApp User'
            try:
                customer = Customer.objects.filter(phone_number=customer_phone).first()
            except Exception:
                pass

        order = ProductOrder.objects.create(
            customer=customer,
            contact=contact,
            customer_name=customer_name,
            customer_phone=customer_phone,
            product=product,
            product_name=product_name,
            product_sku=product_sku,
            quantity=1,
            unit_price=unit_price,
            total_price=unit_price,
            status='pending',
            customer_notes='Enquiry from WhatsApp catalog flow',
        )

        context['enquiry_saved'] = True
        context['enquiry_reference'] = order.order_number
        logger.info(
            f"save_product_enquiry: Created enquiry {order.order_number} "
            f"for '{product_name}'"
        )

    except Exception as exc:
        logger.error(f"save_product_enquiry error: {exc}", exc_info=True)
        context['enquiry_saved'] = False
        context['enquiry_reference'] = ''

    return context
