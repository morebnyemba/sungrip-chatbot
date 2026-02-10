"""
WhatsApp Flow JSON definition for Solar Quote Request.

This file contains the WhatsApp Flow JSON structure for the interactive
solar quote form that customers can fill out directly in WhatsApp.

Following conventions from morebnyemba/Kalai-Safaris.
"""

# Metadata for the solar quote WhatsApp flow
SOLAR_QUOTE_WHATSAPP_FLOW_METADATA = {
    'name': 'solar_quote',
    'friendly_name': 'Solar Quote Form',
    'description': 'Interactive WhatsApp flow for collecting solar quote information',
    'is_active': True,
    'flow_definition_name': 'solar_quote_request',  # Links to traditional flow
}

# WhatsApp Flow JSON structure (simplified example)
# This follows Meta's WhatsApp Flow JSON schema
SOLAR_QUOTE_WHATSAPP_FLOW = {
    "version": "3.0",
    "screens": [
        {
            "id": "QUESTION_ONE",
            "title": "Solar Quote Request",
            "data": {},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "Form",
                        "name": "flow_path",
                        "children": [
                            {
                                "type": "TextHeading",
                                "text": "Get Your Solar Quote"
                            },
                            {
                                "type": "TextSubheading",
                                "text": "Please provide the following information:"
                            },
                            {
                                "type": "TextInput",
                                "name": "monthly_bill",
                                "label": "Average Monthly Electricity Bill (USD)",
                                "input-type": "number",
                                "required": True,
                                "helper-text": "Enter your average monthly electricity bill"
                            },
                            {
                                "type": "TextInput",
                                "name": "roof_type",
                                "label": "Roof Type",
                                "input-type": "text",
                                "required": True,
                                "helper-text": "e.g., tile, metal, asbestos, concrete"
                            },
                            {
                                "type": "TextInput",
                                "name": "location",
                                "label": "Location/City",
                                "input-type": "text",
                                "required": True,
                                "helper-text": "Enter your city or region"
                            },
                            {
                                "type": "Footer",
                                "label": "Submit",
                                "on-click-action": {
                                    "name": "complete",
                                    "payload": {
                                        "monthly_bill": "${form.monthly_bill}",
                                        "roof_type": "${form.roof_type}",
                                        "location": "${form.location}"
                                    }
                                }
                            }
                        ]
                    }
                ]
            }
        }
    ]
}
