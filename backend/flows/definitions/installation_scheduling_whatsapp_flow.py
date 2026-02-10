"""
WhatsApp Flow JSON definition for Installation Scheduling.

This file contains the WhatsApp Flow JSON structure for the interactive
installation scheduling form.

Following conventions from morebnyemba/Kalai-Safaris.
"""

# Metadata for the installation scheduling WhatsApp flow
INSTALLATION_SCHEDULING_WHATSAPP_FLOW_METADATA = {
    'name': 'installation_scheduling',
    'friendly_name': 'Installation Scheduling Form',
    'description': 'Interactive WhatsApp flow for scheduling solar installation appointments',
    'is_active': True,
    'flow_definition_name': 'installation_scheduling',  # Links to traditional flow
}

# WhatsApp Flow JSON structure (simplified example)
INSTALLATION_SCHEDULING_WHATSAPP_FLOW = {
    "version": "3.0",
    "screens": [
        {
            "id": "SCHEDULING_FORM",
            "title": "Schedule Installation",
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
                                "text": "Schedule Your Installation"
                            },
                            {
                                "type": "TextSubheading",
                                "text": "Please select your preferred installation date"
                            },
                            {
                                "type": "DatePicker",
                                "name": "preferred_date",
                                "label": "Preferred Installation Date",
                                "required": True,
                                "min-date": "2024-01-01",
                                "max-date": "2025-12-31",
                                "helper-text": "Choose a date for your solar installation"
                            },
                            {
                                "type": "TextInput",
                                "name": "contact_name",
                                "label": "Contact Name",
                                "input-type": "text",
                                "required": True,
                                "helper-text": "Your full name"
                            },
                            {
                                "type": "TextInput",
                                "name": "phone_number",
                                "label": "Phone Number",
                                "input-type": "phone",
                                "required": True,
                                "helper-text": "Contact number for confirmation"
                            },
                            {
                                "type": "Footer",
                                "label": "Submit",
                                "on-click-action": {
                                    "name": "complete",
                                    "payload": {
                                        "preferred_date": "${form.preferred_date}",
                                        "contact_name": "${form.contact_name}",
                                        "phone_number": "${form.phone_number}"
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
