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
