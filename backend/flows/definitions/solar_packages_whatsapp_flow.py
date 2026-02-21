"""
WhatsApp Flow JSON definition for Solar Package Selection.

This file contains the WhatsApp Flow JSON structure for the interactive
solar package browsing and selection form.

Following conventions from morebnyemba/hanna.
"""

# Data schema shared across all screens
_PACKAGES_DATA = {
    "package": {
        "type": "string",
        "__example__": "medium_home"
    },
    "property_type": {
        "type": "string",
        "__example__": "residential"
    },
    "customer_name": {
        "type": "string",
        "__example__": "Jane Doe"
    },
    "phone_number": {
        "type": "string",
        "__example__": "+263771234567"
    },
    "location": {
        "type": "string",
        "__example__": "Harare"
    }
}

SOLAR_PACKAGES_WHATSAPP_FLOW = {
    "version": "7.3",
    "screens": [
        {
            "id": "WELCOME",
            "title": "Solar Packages",
            "data": {**_PACKAGES_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Browse Solar Packages"
                    },
                    {
                        "type": "TextBody",
                        "text": "Explore our range of solar packages designed for various power needs. Select the option that best fits your requirements."
                    },
                    {
                        "type": "Footer",
                        "label": "Get Started",
                        "on-click-action": {
                            "name": "navigate",
                            "next": {
                                "type": "screen",
                                "name": "PACKAGE_SELECT"
                            },
                            "payload": {
                                "package": "",
                                "property_type": "",
                                "customer_name": "",
                                "phone_number": "",
                                "location": ""
                            }
                        }
                    }
                ]
            }
        },
        {
            "id": "PACKAGE_SELECT",
            "title": "Select a Package",
            "data": {**_PACKAGES_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Choose Your Package"
                    },
                    {
                        "type": "RadioButtonsGroup",
                        "name": "package",
                        "label": "Package size",
                        "required": True,
                        "data-source": [
                            {"id": "small_home", "title": "Essential / Light Use"},
                            {"id": "medium_home", "title": "Standard / Medium Use"},
                            {"id": "large_home", "title": "Premium / Heavy Use"},
                            {"id": "small_business", "title": "Small Business / Commercial"}
                        ]
                    },
                    {
                        "type": "RadioButtonsGroup",
                        "name": "property_type",
                        "label": "Property type",
                        "required": True,
                        "data-source": [
                            {"id": "residential", "title": "Residential"},
                            {"id": "commercial", "title": "Commercial"}
                        ]
                    },
                    {
                        "type": "Footer",
                        "label": "Continue",
                        "on-click-action": {
                            "name": "navigate",
                            "next": {
                                "type": "screen",
                                "name": "CONTACT_INFO"
                            },
                            "payload": {
                                "package": "${form.package}",
                                "property_type": "${form.property_type}",
                                "customer_name": "${data.customer_name}",
                                "phone_number": "${data.phone_number}",
                                "location": "${data.location}"
                            }
                        }
                    }
                ]
            }
        },
        {
            "id": "CONTACT_INFO",
            "title": "Your Details",
            "data": {**_PACKAGES_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Contact Information"
                    },
                    {
                        "type": "TextInput",
                        "name": "customer_name",
                        "label": "Full Name",
                        "required": True,
                        "input-type": "text",
                        "helper-text": "Your full name"
                    },
                    {
                        "type": "TextInput",
                        "name": "phone_number",
                        "label": "Phone Number",
                        "required": True,
                        "input-type": "phone",
                        "helper-text": "e.g., +263771234567"
                    },
                    {
                        "type": "TextInput",
                        "name": "location",
                        "label": "City / Location",
                        "required": True,
                        "input-type": "text",
                        "helper-text": "Enter your city or town"
                    },
                    {
                        "type": "Footer",
                        "label": "Submit",
                        "on-click-action": {
                            "name": "complete",
                            "payload": {
                                "package": "${data.package}",
                                "property_type": "${data.property_type}",
                                "customer_name": "${form.customer_name}",
                                "phone_number": "${form.phone_number}",
                                "location": "${form.location}"
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

# Metadata for the solar packages WhatsApp flow
SOLAR_PACKAGES_WHATSAPP_FLOW_METADATA = {
    "name": "solar_packages_whatsapp",
    "friendly_name": "Solar Package Selection (Interactive)",
    "description": "Interactive WhatsApp flow for browsing and selecting solar packages",
    "trigger_keywords": [],
    "is_active": True,
}
