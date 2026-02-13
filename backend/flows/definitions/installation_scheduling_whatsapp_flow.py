"""
WhatsApp Flow JSON definition for Installation Scheduling.

This file contains the WhatsApp Flow JSON structure for the interactive
installation scheduling form.

Following conventions from morebnyemba/hanna.
"""

# Data schema shared across all screens
_INSTALLATION_DATA = {
    "contact_name": {
        "type": "string",
        "__example__": "John Doe"
    },
    "phone_number": {
        "type": "string",
        "__example__": "+263771234567"
    },
    "alt_contact": {
        "type": "string",
        "__example__": "+263772345678"
    },
    "preferred_date": {
        "type": "string",
        "__example__": "2025-12-25"
    },
    "time_preference": {
        "type": "string",
        "__example__": "morning"
    },
    "address": {
        "type": "string",
        "__example__": "456 Solar Avenue, Bulawayo"
    }
}

INSTALLATION_SCHEDULING_WHATSAPP_FLOW = {
    "version": "7.3",
    "screens": [
        {
            "id": "WELCOME",
            "title": "Schedule Installation",
            "data": {**_INSTALLATION_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Schedule Your Installation"
                    },
                    {
                        "type": "TextBody",
                        "text": "Let's book a convenient time for your solar installation. This should only take a minute."
                    },
                    {
                        "type": "Footer",
                        "label": "Get Started",
                        "on-click-action": {
                            "name": "navigate",
                            "next": {
                                "type": "screen",
                                "name": "CUSTOMER_INFO"
                            },
                            "payload": {
                                "contact_name": "",
                                "phone_number": "",
                                "alt_contact": "",
                                "preferred_date": "",
                                "time_preference": "",
                                "address": ""
                            }
                        }
                    }
                ]
            }
        },
        {
            "id": "CUSTOMER_INFO",
            "title": "Your Information",
            "data": {**_INSTALLATION_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Contact Information"
                    },
                    {
                        "type": "TextInput",
                        "name": "contact_name",
                        "label": "Contact Name",
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
                        "name": "alt_contact",
                        "label": "Alternative Contact (Optional)",
                        "required": False,
                        "input-type": "phone",
                        "helper-text": "Backup number if we can't reach you"
                    },
                    {
                        "type": "Footer",
                        "label": "Continue",
                        "on-click-action": {
                            "name": "navigate",
                            "next": {
                                "type": "screen",
                                "name": "SCHEDULE"
                            },
                            "payload": {
                                "contact_name": "${form.contact_name}",
                                "phone_number": "${form.phone_number}",
                                "alt_contact": "${form.alt_contact}",
                                "preferred_date": "${data.preferred_date}",
                                "time_preference": "${data.time_preference}",
                                "address": "${data.address}"
                            }
                        }
                    }
                ]
            }
        },
        {
            "id": "SCHEDULE",
            "title": "Preferred Schedule",
            "data": {**_INSTALLATION_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Pick a Date & Time"
                    },
                    {
                        "type": "DatePicker",
                        "name": "preferred_date",
                        "label": "Preferred Installation Date",
                        "required": True
                    },
                    {
                        "type": "RadioButtonsGroup",
                        "name": "time_preference",
                        "label": "Preferred Time of Day",
                        "required": True,
                        "data-source": [
                            {"id": "morning", "title": "Morning (8am - 12pm)"},
                            {"id": "afternoon", "title": "Afternoon (12pm - 5pm)"}
                        ]
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
                                "contact_name": "${data.contact_name}",
                                "phone_number": "${data.phone_number}",
                                "alt_contact": "${data.alt_contact}",
                                "preferred_date": "${form.preferred_date}",
                                "time_preference": "${form.time_preference}",
                                "address": "${data.address}"
                            }
                        }
                    }
                ]
            }
        },
        {
            "id": "LOCATION",
            "title": "Installation Location",
            "data": {**_INSTALLATION_DATA},
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "TextHeading",
                        "text": "Installation Address"
                    },
                    {
                        "type": "TextInput",
                        "name": "address",
                        "label": "Full Installation Address",
                        "required": True,
                        "input-type": "text",
                        "helper-text": "Provide the complete address for the installation"
                    },
                    {
                        "type": "TextBody",
                        "text": "Note: You can share your location pin via WhatsApp after submitting this form."
                    },
                    {
                        "type": "Footer",
                        "label": "Submit Booking",
                        "on-click-action": {
                            "name": "complete",
                            "payload": {
                                "contact_name": "${data.contact_name}",
                                "phone_number": "${data.phone_number}",
                                "alt_contact": "${data.alt_contact}",
                                "preferred_date": "${data.preferred_date}",
                                "time_preference": "${data.time_preference}",
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

# Metadata for the installation scheduling WhatsApp flow
INSTALLATION_SCHEDULING_WHATSAPP_FLOW_METADATA = {
    "name": "installation_scheduling_whatsapp",
    "friendly_name": "Installation Scheduling (Interactive)",
    "description": "Interactive WhatsApp flow for scheduling solar installation appointments",
    "trigger_keywords": [],
    "is_active": True,
    "flow_definition_name": "installation_scheduling",
}
