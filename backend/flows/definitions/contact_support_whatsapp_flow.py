"""
WhatsApp Flow JSON definition for Contact Support.

This file contains the WhatsApp Flow JSON structure for the interactive
support request form that customers can fill out directly in WhatsApp.

Following conventions from morebnyemba/hanna.
"""

# Data schema shared across all screens
_SUPPORT_DATA = {
    "support_category": {
        "type": "string",
        "__example__": "technical_issues"
    },
    "issue_description": {
        "type": "string",
        "__example__": "Inverter showing error code E04"
    },
    "contact_preference": {
        "type": "string",
        "__example__": "whatsapp"
    },
    "contact_info": {
        "type": "string",
        "__example__": "+263771234567"
    }
}

CONTACT_SUPPORT_WHATSAPP_FLOW = {
    "version": "7.3",
    "screens": [
        {
            "id": "WELCOME",
            "title": "Contact Support",
            "data": {**_SUPPORT_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Welcome to Support"
                    },
                    {
                        "type": "TextBody",
                        "text": "We're here to help! Tell us about your issue and we'll get back to you as soon as possible."
                    },
                    {
                        "type": "Footer",
                        "label": "Get Started",
                        "on-click-action": {
                            "name": "navigate",
                            "next": {
                                "type": "screen",
                                "name": "SUPPORT_TYPE"
                            },
                            "payload": {
                                "support_category": "",
                                "issue_description": "",
                                "contact_preference": "",
                                "contact_info": ""
                            }
                        }
                    }
                ]
            }
        },
        {
            "id": "SUPPORT_TYPE",
            "title": "Support Category",
            "data": {**_SUPPORT_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "What do you need help with?"
                    },
                    {
                        "type": "RadioButtonsGroup",
                        "name": "support_category",
                        "label": "Select a category",
                        "required": True,
                        "data-source": [
                            {"id": "technical_issues", "title": "Technical Issues"},
                            {"id": "billing", "title": "Billing & Payments"},
                            {"id": "installation_support", "title": "Installation Support"},
                            {"id": "product_info", "title": "Product Information"},
                            {"id": "other", "title": "Other"}
                        ]
                    },
                    {
                        "type": "Footer",
                        "label": "Continue",
                        "on-click-action": {
                            "name": "navigate",
                            "next": {
                                "type": "screen",
                                "name": "DETAILS"
                            },
                            "payload": {
                                "support_category": "${form.support_category}",
                                "issue_description": "${data.issue_description}",
                                "contact_preference": "${data.contact_preference}",
                                "contact_info": "${data.contact_info}"
                            }
                        }
                    }
                ]
            }
        },
        {
            "id": "DETAILS",
            "title": "Issue Details",
            "data": {**_SUPPORT_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Describe Your Issue"
                    },
                    {
                        "type": "TextInput",
                        "name": "issue_description",
                        "label": "Issue Description",
                        "required": True,
                        "input-type": "text",
                        "helper-text": "Please describe the problem you're experiencing"
                    },
                    {
                        "type": "RadioButtonsGroup",
                        "name": "contact_preference",
                        "label": "How would you like us to reach you?",
                        "required": True,
                        "data-source": [
                            {"id": "whatsapp", "title": "WhatsApp"},
                            {"id": "phone_call", "title": "Phone Call"},
                            {"id": "email", "title": "Email"}
                        ]
                    },
                    {
                        "type": "TextInput",
                        "name": "contact_info",
                        "label": "Contact Details",
                        "required": True,
                        "input-type": "text",
                        "helper-text": "Phone number or email address"
                    },
                    {
                        "type": "Footer",
                        "label": "Submit Request",
                        "on-click-action": {
                            "name": "complete",
                            "payload": {
                                "support_category": "${data.support_category}",
                                "issue_description": "${form.issue_description}",
                                "contact_preference": "${form.contact_preference}",
                                "contact_info": "${form.contact_info}"
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

# Metadata for the contact support WhatsApp flow
CONTACT_SUPPORT_WHATSAPP_FLOW_METADATA = {
    "name": "contact_support_whatsapp",
    "friendly_name": "Contact Support (Interactive)",
    "description": "Interactive WhatsApp flow for submitting support requests",
    "trigger_keywords": [],
    "is_active": True,
}
