# backend/notifications/utils.py

"""
Jinja2 template rendering utilities for the notifications system.
Ported from morebnyemba/hanna's notifications/utils.py.
"""

import logging
from jinja2 import Environment, Undefined
from django.conf import settings

logger = logging.getLogger(__name__)


class SilentUndefined(Undefined):
    """A Jinja2 Undefined class that fails silently by returning an empty string."""

    def _fail_with_undefined_error(self, *args, **kwargs):
        return ''


# Shared Jinja2 environment with silent undefined handling
jinja_env = Environment(undefined=SilentUndefined)


def render_template_string(template_string: str, context: dict) -> str:
    """
    Renders a Jinja2 template string with a given context.

    Args:
        template_string: The string containing Jinja2 template syntax.
        context: A dictionary of variables to be used in rendering.

    Returns:
        The rendered string.
    """
    if not isinstance(template_string, str):
        return str(template_string)
    try:
        template = jinja_env.from_string(template_string)
        return template.render(context)
    except Exception as e:
        logger.error(
            f"Jinja2 template rendering failed: {e}. Template: '{template_string}'",
            exc_info=False,
        )
        return template_string


def get_versioned_template_name(template_name: str) -> str:
    """
    Returns the template name with the version suffix appended.

    Used when sending template messages to Meta's WhatsApp API so the name
    matches the versioned name synced to Meta.

    Example:
        >>> get_versioned_template_name('sungrip_new_product_order')
        'sungrip_new_product_order_v1_01'
    """
    version_suffix = getattr(settings, 'META_SYNC_VERSION_SUFFIX', 'v1_01')
    return f"{template_name}_{version_suffix}"
