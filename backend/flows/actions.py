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


# ---------------------------------------------------------------------------
# Shared helper: enrich Customer record with data collected during flows
# ---------------------------------------------------------------------------

def _enrich_customer_profile(contact, context: dict) -> None:
    """
    Progressively fill empty fields on the Customer record using data
    the user provided during a flow.  Only writes to fields that are
    still blank — never overwrites existing values.

    Called by every save action so the Customer profile gets richer
    with each interaction.
    """
    from customers.models import Customer

    if not contact:
        return

    try:
        customer = Customer.objects.filter(
            phone_number=contact.phone_number
        ).first()
        if not customer:
            return

        updated_fields = []

        # --- Name ---
        customer_name = context.get('customer_name', '')
        if customer_name and (not customer.full_name or customer.full_name == 'WhatsApp User'):
            customer.full_name = customer_name
            updated_fields.append('full_name')

        # --- Customer type from property_type ---
        property_type = context.get('property_type', '')
        PROPERTY_TYPE_MAP = {
            'residential': 'residential',
            'commercial': 'commercial',
            'industrial': 'industrial',
        }
        if property_type and customer.customer_type == 'residential':
            # Normalise display labels back to DB values
            raw = property_type.lower()
            for key, val in PROPERTY_TYPE_MAP.items():
                if key in raw:
                    if customer.customer_type != val:
                        customer.customer_type = val
                        updated_fields.append('customer_type')
                    break

        # --- City from location ---
        location = context.get('location', '')
        if location and not customer.city:
            customer.city = str(location)[:100]
            updated_fields.append('city')

        # --- Address from installation_address or delivery_address ---
        address = (
            context.get('installation_address')
            or context.get('delivery_address')
            or ''
        )
        if address and not customer.address_line1:
            customer.address_line1 = str(address)[:255]
            updated_fields.append('address_line1')

        # --- GPS from location_pin ---
        location_pin = context.get('location_pin')
        if isinstance(location_pin, dict):
            lat = location_pin.get('latitude')
            lng = location_pin.get('longitude')
            if lat and lng and not customer.gps_latitude:
                customer.gps_latitude = lat
                customer.gps_longitude = lng
                updated_fields.extend(['gps_latitude', 'gps_longitude'])

        if updated_fields:
            customer.save(update_fields=updated_fields)
            logger.info(
                f"_enrich_customer_profile: Updated {updated_fields} "
                f"for {contact.phone_number}"
            )
    except Exception as exc:
        logger.warning(f"_enrich_customer_profile error: {exc}")


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
        - monthly_bill, roof_type, property_type, location, location_pin
    """
    from orders.models import QuoteRequest
    from customers.models import Customer
    
    save_to_var = params.get('save_to_variable', 'quote_request_saved')
    
    try:
        # Generate unique request ID
        request_id = f"QUOTE-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        # Extract data from context
        monthly_bill = context.get('monthly_bill')
        gadgets_to_power = context.get('gadgets_to_power', '')
        roof_type = context.get('roof_type', '')
        property_type = context.get('property_type', '')
        location = context.get('location', '')
        location_pin = context.get('location_pin')
        customer_name = context.get('customer_name') or (
            getattr(contact, 'profile_name', None) or getattr(contact, 'name', 'Unknown')
            if contact else 'Unknown'
        )
        
        # Try to find customer
        customer = None
        if contact:
            customer = Customer.objects.filter(
                phone_number=contact.phone_number
            ).first()
        
        # Build notes from extra fields
        notes_parts = []
        if property_type:
            notes_parts.append(f"Property type: {property_type}")
        if location_pin and isinstance(location_pin, dict):
            lat = location_pin.get('latitude', '')
            lng = location_pin.get('longitude', '')
            if lat and lng:
                notes_parts.append(f"GPS: {lat}, {lng}")
        elif location_pin and str(location_pin) != 'skip_location':
            notes_parts.append(f"Location pin: {location_pin}")

        # Create QuoteRequest in database
        quote_request_obj = QuoteRequest.objects.create(
            customer=customer,
            contact=contact,
            request_id=request_id,
            customer_name=customer_name,
            monthly_bill=monthly_bill,
            gadgets_to_power=gadgets_to_power,
            roof_type=roof_type,
            location=location,
            notes='\n'.join(notes_parts),
            status='pending'
        )
        
        quote_request = {
            'success': True,
            'id': quote_request_obj.id,
            'request_id': request_id,
            'monthly_bill': monthly_bill,
            'gadgets_to_power': gadgets_to_power,
            'roof_type': roof_type,
            'property_type': property_type,
            'location': location,
            'customer_name': customer_name,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Quote request saved to database: {quote_request}")
        
        context[save_to_var] = quote_request

        # Enrich Customer profile with collected data
        _enrich_customer_profile(contact, context)
        
    except Exception as e:
        logger.error(f"Error saving quote request: {e}", exc_info=True)
        context[save_to_var] = {
            'success': False,
            'message': f'Error saving quote request: {str(e)}'
        }
    
    return context


@register_flow_action('save_installation_request')
def save_installation_request(contact, context: dict, params: dict) -> dict:
    """
    Saves an installation scheduling request from the chatbot flow.

    Uses context variables:
        system_size, payment_preference, preferred_date, time_preference,
        installation_address, location_pin, additional_notes, customer_name
    """
    from orders.models import InstallationRequest
    from customers.models import Customer

    save_to_var = params.get('save_to_variable', 'install_request_saved')

    try:
        request_id = f"INST-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        customer_name = context.get('customer_name') or (
            getattr(contact, 'profile_name', None) or 'Unknown'
            if contact else 'Unknown'
        )

        customer = None
        if contact:
            customer = Customer.objects.filter(
                phone_number=contact.phone_number
            ).first()

        location_pin = context.get('location_pin')
        location_data = {}
        if isinstance(location_pin, dict):
            location_data = location_pin
        elif location_pin and str(location_pin) != 'skip_location':
            location_data = {'raw': str(location_pin)}

        obj = InstallationRequest.objects.create(
            customer=customer,
            contact=contact,
            request_id=request_id,
            customer_name=customer_name,
            system_size=context.get('system_size', ''),
            payment_preference=context.get('payment_preference', ''),
            preferred_date=context.get('preferred_date', ''),
            time_preference=context.get('time_preference', ''),
            installation_address=context.get('installation_address', ''),
            location_pin=location_data,
            additional_notes=context.get('additional_notes', ''),
            status='pending',
        )

        context[save_to_var] = {
            'success': True,
            'id': obj.id,
            'request_id': request_id,
            'timestamp': timezone.now().isoformat(),
        }
        logger.info(f"Installation request saved: {request_id}")

        # Enrich Customer profile with collected data
        _enrich_customer_profile(contact, context)

    except Exception as e:
        logger.error(f"Error saving installation request: {e}", exc_info=True)
        context[save_to_var] = {
            'success': False,
            'message': str(e),
        }

    return context


@register_flow_action('save_support_request')
def save_support_request(contact, context: dict, params: dict) -> dict:
    """
    Saves a support request from the chatbot flow.

    Uses context variables:
        support_category, issue_details, contact_method, customer_name
    """
    from orders.models import SupportRequest
    from customers.models import Customer

    save_to_var = params.get('save_to_variable', 'support_request_saved')

    try:
        request_id = f"SUP-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        customer_name = context.get('customer_name') or (
            getattr(contact, 'profile_name', None) or 'Unknown'
            if contact else 'Unknown'
        )

        customer = None
        if contact:
            customer = Customer.objects.filter(
                phone_number=contact.phone_number
            ).first()

        obj = SupportRequest.objects.create(
            customer=customer,
            contact=contact,
            request_id=request_id,
            customer_name=customer_name,
            support_category=context.get('support_category', ''),
            issue_details=context.get('issue_details', ''),
            contact_method=context.get('contact_method', ''),
            status='pending',
        )

        context[save_to_var] = {
            'success': True,
            'id': obj.id,
            'request_id': request_id,
            'timestamp': timezone.now().isoformat(),
        }
        logger.info(f"Support request saved: {request_id}")

        # Enrich Customer profile with collected data
        _enrich_customer_profile(contact, context)

    except Exception as e:
        logger.error(f"Error saving support request: {e}", exc_info=True)
        context[save_to_var] = {
            'success': False,
            'message': str(e),
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
            lines.append(
                f"📦 *{pkg.name.upper()}*{popular_badge}\n"
                f"• {_fmt_kva(pkg.system_size_kw)} kVA Solar System\n"
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


def _fmt_kva(val):
    """Format a Decimal kVA value without trailing zeros (3.50 → 3.5)."""
    return f"{float(val):g}"


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
                        f"{_fmt_kva(pkg.system_size_kw)}kVA · ${pkg.deposit_amount:,.0f} dep "
                        f"+ ${installment:,.0f}×{num_payments}"
                    )
                else:
                    monthly = pkg.total_price / pkg.installment_months
                    desc = f"{_fmt_kva(pkg.system_size_kw)}kVA · ${pkg.total_price:,.0f} (${monthly:,.0f}/mo)"
            else:
                desc = f"{_fmt_kva(pkg.system_size_kw)}kVA · ${pkg.total_price:,.0f}"

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

        # Always add a "Get a Quote" option so users can request
        # a custom system quote instead of picking a fixed package.
        sections.append({
            'title': '📋 Something Else?',
            'rows': [{
                'id': 'get_quote',
                'title': '📋 Get a Quote',
                'description': 'Request a custom solar system quote'
            }]
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
        lines.append(f"⚡ *System Size:* {_fmt_kva(pkg.system_size_kw)} kVA")

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
        context['package_system_size'] = f"{_fmt_kva(pkg.system_size_kw)} kVA"

        # Map system_size_kw → raw interactive ID used by LABEL_MAPS
        kva_to_id = {3.5: '3.5kva', 4.2: '4.2kva', 6.2: '6.2kva'}
        context['system_size'] = kva_to_id.get(
            float(pkg.system_size_kw), f"{_fmt_kva(pkg.system_size_kw)}kva"
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

        notification_ctx = context.copy()
        # Ensure customer_phone is available for templates
        if contact and 'customer_phone' not in notification_ctx:
            notification_ctx['customer_phone'] = getattr(
                contact, 'phone_number', ''
            )
        notification_ctx.setdefault('timestamp', timezone.now().strftime('%Y-%m-%d %H:%M'))

        # Flatten saved request data so template variables are available
        # at the top level (quote_request_saved, installation_request_saved).
        for saved_key in ('quote_request_saved', 'installation_request_saved'):
            saved_data = notification_ctx.get(saved_key)
            if isinstance(saved_data, dict):
                for field, val in saved_data.items():
                    if field not in ('success', 'id', 'timestamp') and val is not None and val != '':
                        notification_ctx.setdefault(field, val)

        # Auto-compute Google Maps link from location_pin if not already set
        if 'google_maps_link' not in notification_ctx:
            loc_pin = notification_ctx.get('location_pin')
            if isinstance(loc_pin, dict):
                lat = loc_pin.get('latitude')
                lng = loc_pin.get('longitude')
                if lat and lng:
                    notification_ctx['google_maps_link'] = (
                        f"\U0001f5fa\ufe0f *Map:* https://www.google.com/maps?q={lat},{lng}\n"
                    )
            if 'google_maps_link' not in notification_ctx:
                notification_ctx['google_maps_link'] = ''

        queue_notifications_to_users(
            template_name=template_name,
            template_context=notification_ctx,
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


# ---------------------------------------------------------------------------
#  WhatsApp Commerce Catalog  (matches hanna pattern)
# ---------------------------------------------------------------------------

@register_flow_action('send_catalog_message')
def send_catalog_message(contact, context: dict, params: dict) -> dict:
    """
    Send the WhatsApp Commerce Catalog to the user.

    Instead of listing products inside the chatbot, this opens WhatsApp's
    native catalog browsing UI.  The user adds items to a cart and submits
    an order — WhatsApp then posts an ``order`` webhook that we handle in
    ``_handle_order_message`` (meta_integration/views.py).

    Expected params (all optional):
        body_text:   Catalog body text shown to the user.
        footer_text: Small footer line.
        thumbnail_sku: SKU of the product whose image becomes the header.
    """
    from meta_integration.models import MetaAppConfig

    try:
        active_config = MetaAppConfig.objects.get_active_config()
        catalog_id = active_config.catalog_id
    except Exception:
        catalog_id = None

    if not catalog_id:
        logger.error("send_catalog_message: No catalog_id configured in MetaAppConfig")
        context['_catalog_sent'] = False
        return context

    body_text = params.get(
        'body_text',
        "🛒 *Sungrip Solar Product Catalog*\n\n"
        "Browse our range of solar panels, inverters, batteries and accessories below.\n\n"
        "Add items to your cart and submit your order — we'll confirm it right here on WhatsApp!"
    )
    footer_text = params.get('footer_text', 'Tap on a product to view details')
    thumbnail_sku = params.get('thumbnail_sku')

    interactive_payload = {
        "type": "catalog_message",
        "body": {"text": body_text},
        "action": {
            "name": "catalog_message",
        },
    }

    if footer_text:
        interactive_payload["footer"] = {"text": footer_text}

    # Optional: highlight a specific product as the catalog thumbnail
    if thumbnail_sku:
        interactive_payload["action"]["parameters"] = {
            "thumbnail_product_retailer_id": thumbnail_sku,
        }

    context['_dynamic_messages'] = context.get('_dynamic_messages', [])
    context['_dynamic_messages'].append({
        'type': 'send_whatsapp_message',
        'recipient_wa_id': contact.phone_number,
        'message_type': 'interactive',
        'data': interactive_payload,
    })
    context['_catalog_sent'] = True

    logger.info(
        f"send_catalog_message: Queued catalog message for "
        f"{contact.phone_number} (catalog_id={catalog_id})"
    )
    return context


# ---------------------------------------------------------------------------
#  Save delivery info after catalog order  (order_delivery_info flow)
# ---------------------------------------------------------------------------

@register_flow_action('save_delivery_info')
def save_delivery_info(contact, context: dict, params: dict) -> dict:
    """
    Persist delivery details collected by the ``order_delivery_info`` flow,
    send the order confirmation to the customer, and notify the team.

    Expected context variables (set by the flow's question steps):
        order_id          – PK of the Order created by process_order_from_catalog
        order_number      – Human-readable order number (e.g. WA-12345)
        items_text        – Formatted line items string
        total_amount      – Total formatted as e.g. "80.00"
        currency          – e.g. "USD"
        recipient_name    – Full name of the delivery recipient
        recipient_phone   – Phone number for the recipient
        delivery_address  – Street / area / city
        location_pin      – Location dict from WhatsApp, "skip_location", or text
        customer_name     – Name of the ordering customer (for notification)
    """
    from orders.models import Order, ProductOrder
    from customers.models import Customer
    from meta_integration.utils import send_whatsapp_message

    order_id = context.get('order_id')
    order_number = context.get('order_number', 'N/A')
    items_text = context.get('items_text', '')
    total_amount = context.get('total_amount', '0.00')
    currency = context.get('currency', 'USD')
    recipient_name = context.get('recipient_name', '')
    recipient_phone = context.get('recipient_phone', '')
    delivery_address = context.get('delivery_address', '')
    location_pin = context.get('location_pin')
    customer_name = context.get('customer_name', '')

    # ── 1. Determine location text ────────────────────────────────
    location_text = ''
    gps_lat = None
    gps_lng = None
    if isinstance(location_pin, dict):
        # WhatsApp location object: {'latitude': ..., 'longitude': ..., ...}
        gps_lat = location_pin.get('latitude')
        gps_lng = location_pin.get('longitude')
        loc_name = location_pin.get('name', '')
        loc_addr = location_pin.get('address', '')
        if gps_lat and gps_lng:
            location_text = f"📍 {loc_name or loc_addr or f'{gps_lat}, {gps_lng}'}"
    elif location_pin and str(location_pin) != 'skip_location':
        location_text = f"📍 {location_pin}"

    # ── 2. Update Order with delivery details ─────────────────────
    if order_id:
        try:
            order = Order.objects.get(pk=order_id)
            delivery_notes = (
                f"Recipient: {recipient_name}\n"
                f"Phone: {recipient_phone}\n"
                f"Address: {delivery_address}"
            )
            if location_text:
                delivery_notes += f"\n{location_text}"

            # Append delivery info to customer_notes
            existing_notes = order.customer_notes or ''
            order.customer_notes = (
                f"{existing_notes}\n\n--- Delivery Details ---\n"
                f"{delivery_notes}"
            ).strip()
            order.save(update_fields=['customer_notes', 'updated_at'])
            logger.info(f"save_delivery_info: Updated order {order_number} with delivery details")

            # Also update linked ProductOrder records with delivery info
            try:
                ProductOrder.objects.filter(full_order=order).update(
                    delivery_address=delivery_address,
                    delivery_method='delivery',
                )
            except Exception as po_exc:
                logger.warning(f"save_delivery_info: Failed to update ProductOrders: {po_exc}")

        except Order.DoesNotExist:
            logger.error(f"save_delivery_info: Order {order_id} not found")
        except Exception as exc:
            logger.error(f"save_delivery_info: Error updating order: {exc}", exc_info=True)

    # ── 3. Enrich Customer profile with delivery details + GPS ────
    _enrich_customer_profile(contact, context)

    # ── 4. Send confirmation message to customer ──────────────────
    delivery_block = (
        f"📦 *Delivery To:*\n"
        f"  👤 {recipient_name}\n"
        f"  📱 {recipient_phone}\n"
        f"  🏠 {delivery_address}"
    )
    if location_text:
        delivery_block += f"\n  {location_text}"

    confirmation = (
        f"✅ *Order {order_number} — Confirmed!*\n\n"
        f"📋 *Items:*\n{items_text}\n\n"
        f"💰 *Total:* ${total_amount} {currency}\n\n"
        f"{delivery_block}\n\n"
        f"Our team will be in touch to arrange delivery. Thank you! 🙏"
    )

    context['_dynamic_messages'] = context.get('_dynamic_messages', [])
    context['_dynamic_messages'].append({
        'type': 'send_whatsapp_message',
        'recipient_wa_id': contact.phone_number,
        'message_type': 'text',
        'data': {'body': confirmation},
    })

    # ── 5. Notify team via notification system ────────────────────
    try:
        from notifications.services import queue_notifications_to_users

        # Build Google Maps link from GPS coordinates if available
        google_maps_link = ''
        if gps_lat and gps_lng:
            google_maps_link = (
                f"🗺️ *Map:* https://www.google.com/maps?q={gps_lat},{gps_lng}\n"
            )

        notification_context = {
            'customer_name': customer_name,
            'customer_phone': contact.phone_number,
            'order_number': order_number,
            'items_summary': items_text,
            'order_total': f"${total_amount} {currency}",
            'recipient_name': recipient_name,
            'recipient_phone': recipient_phone,
            'delivery_address': delivery_address,
            'google_maps_link': google_maps_link,
            'location': location_text or '(not provided)',
            'customer_note': context.get('customer_note', '(none)'),
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M'),
        }
        queue_notifications_to_users(
            template_name='sungrip_new_product_order',
            template_context=notification_context,
            group_names=['Sales Team'],
            related_contact=contact,
        )
    except Exception as exc:
        # Notification failure should not block order completion
        logger.warning(f"Team notification failed for order {order_number}: {exc}")

    logger.info(
        f"save_delivery_info: Completed for order {order_number} — "
        f"recipient={recipient_name}, address={delivery_address}"
    )
    return context
