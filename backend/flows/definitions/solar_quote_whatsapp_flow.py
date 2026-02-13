"""
WhatsApp Flow JSON definition for Solar Quote Request.

This file contains the WhatsApp Flow JSON structure for the interactive
solar quote form that customers can fill out directly in WhatsApp.

Following conventions from morebnyemba/hanna.
"""

# Data schema shared across all screens
_SOLAR_QUOTE_DATA = {
    "roof_type": {
        "type": "string",
        "__example__": "tile"
    },
    "monthly_bill": {
        "type": "string",
        "__example__": "150"
    },
    "system_type": {
        "type": "string",
        "__example__": "hybrid"
    },
    "property_size": {
        "type": "string",
        "__example__": "3"
    },
    "location": {
        "type": "string",
        "__example__": "Harare"
    },
    "address": {
        "type": "string",
        "__example__": "123 Main Street, Harare"
    }
}

SOLAR_QUOTE_WHATSAPP_FLOW = {
    "version": "7.3",
    "screens": [
        {
            "id": "WELCOME",
            "title": "Solar Quote Request",
            "data": {**_SOLAR_QUOTE_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Get Your Solar Quote"
                    },
                    {
                        "type": "TextBody",
                        "text": "Answer a few quick questions and we'll prepare a personalised solar quote for your property."
                    },
                    {
                        "type": "Footer",
                        "label": "Get Started",
                        "on-click-action": {
                            "name": "navigate",
                            "next": {
                                "type": "screen",
                                "name": "PROPERTY_INFO"
                            },
                            "payload": {
                                "roof_type": "",
                                "monthly_bill": "",
                                "system_type": "",
                                "property_size": "",
                                "location": "",
                                "address": ""
                            }
                        }
                    }
                ]
            }
        },
        {
            "id": "PROPERTY_INFO",
            "title": "Property Information",
            "data": {**_SOLAR_QUOTE_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Property Details"
                    },
                    {
                        "type": "RadioButtonsGroup",
                        "name": "roof_type",
                        "label": "What type of roof do you have?",
                        "required": True,
                        "data-source": [
                            {"id": "tile", "title": "Tile Roof"},
                            {"id": "metal", "title": "Metal / IBR Sheet"},
                            {"id": "asbestos", "title": "Asbestos"},
                            {"id": "concrete", "title": "Flat Concrete"},
                            {"id": "thatch", "title": "Thatch"},
                            {"id": "other", "title": "Other / Not Sure"}
                        ]
                    },
                    {
                        "type": "TextInput",
                        "name": "monthly_bill",
                        "label": "Average Monthly Electricity Bill (USD)",
                        "required": True,
                        "input-type": "number",
                        "helper-text": "Enter your average monthly electricity bill"
                    },
                    {
                        "type": "Footer",
                        "label": "Continue",
                        "on-click-action": {
                            "name": "navigate",
                            "next": {
                                "type": "screen",
                                "name": "SYSTEM_PREFERENCES"
                            },
                            "payload": {
                                "roof_type": "${form.roof_type}",
                                "monthly_bill": "${form.monthly_bill}",
                                "system_type": "${data.system_type}",
                                "property_size": "${data.property_size}",
                                "location": "${data.location}",
                                "address": "${data.address}"
                            }
                        }
                    }
                ]
            }
        },
        {
            "id": "SYSTEM_PREFERENCES",
            "title": "System Preferences",
            "data": {**_SOLAR_QUOTE_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "System Preferences"
                    },
                    {
                        "type": "RadioButtonsGroup",
                        "name": "system_type",
                        "label": "Preferred system type",
                        "required": True,
                        "data-source": [
                            {"id": "grid_tie", "title": "Grid-Tie (No Battery)"},
                            {"id": "off_grid", "title": "Off-Grid (Full Battery)"},
                            {"id": "hybrid", "title": "Hybrid (Grid + Battery)"}
                        ]
                    },
                    {
                        "type": "TextInput",
                        "name": "property_size",
                        "label": "Number of Bedrooms",
                        "required": True,
                        "input-type": "number",
                        "helper-text": "Helps us estimate your energy needs"
                    },
                    {
                        "type": "Footer",
                        "label": "Continue",
                        "on-click-action": {
                            "name": "navigate",
                            "next": {
                                "type": "screen",
                                "name": "LOCATION"
                            },
                            "payload": {
                                "roof_type": "${data.roof_type}",
                                "monthly_bill": "${data.monthly_bill}",
                                "system_type": "${form.system_type}",
                                "property_size": "${form.property_size}",
                                "location": "${data.location}",
                                "address": "${data.address}"
                            }
                        }
                    }
                ]
            }
        },
        {
            "id": "LOCATION",
            "title": "Location",
            "data": {**_SOLAR_QUOTE_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Location Details"
                    },
                    {
                        "type": "TextInput",
                        "name": "location",
                        "label": "City / Town",
                        "required": True,
                        "input-type": "text",
                        "helper-text": "Enter your city or town"
                    },
                    {
                        "type": "TextInput",
                        "name": "address",
                        "label": "Full Address",
                        "required": True,
                        "input-type": "text",
                        "helper-text": "Street address for site assessment"
                    },
                    {
                        "type": "TextBody",
                        "text": "Note: You can share your location pin via WhatsApp after submitting this form."
                    },
                    {
                        "type": "Footer",
                        "label": "Submit Quote Request",
                        "on-click-action": {
                            "name": "complete",
                            "payload": {
                                "roof_type": "${data.roof_type}",
                                "monthly_bill": "${data.monthly_bill}",
                                "system_type": "${data.system_type}",
                                "property_size": "${data.property_size}",
                                "location": "${form.location}",
                                "address": "${form.address}"
                            }
                        }
                    }
                ]
            },
            "terminal": True,
            "success": True
        }
    ]
}

# Metadata for the solar quote WhatsApp flow
SOLAR_QUOTE_WHATSAPP_FLOW_METADATA = {
    "name": "solar_quote_whatsapp",
    "friendly_name": "Solar Quote Request (Interactive)",
    "description": "Interactive WhatsApp flow for collecting solar quote information",
    "trigger_keywords": [],
    "is_active": True,
    "flow_definition_name": "solar_quote_request",
}
