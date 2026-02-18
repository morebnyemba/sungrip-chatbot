# backend/flows/definitions/contact_support_flow.py

"""
Contact support flow definition.

Connects customers with the support team by collecting their inquiry
details and preferred contact method.
"""

CONTACT_SUPPORT_FLOW = {
    "name": "contact_support",
    "friendly_name": "Contact Support",
    "description": "Connect customers with support team and collect their inquiry",
    "is_active": True,
    "trigger_keywords": ["support", "help", "contact", "talk to human", "agent"],
    "steps": [
        {
            "name": "welcome",
            "type": "question",
            "is_entry_point": True,
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {
                            "type": "text",
                            "text": "Sungrip Support"
                        },
                        "body": {
                            "text": "👋 Sungrip Solar Support\n\n"
                                   "Our support team is here to help you!\n\n"
                                   "Please select what you need help with:"
                        },
                        "footer": {
                            "text": "Choose a category"
                        },
                        "action": {
                            "button": "Select Category",
                            "sections": [
                                {
                                    "title": "Support Categories",
                                    "rows": [
                                        {
                                            "id": "technical",
                                            "title": "Technical Issues",
                                            "description": "System faults, inverter errors, panel issues"
                                        },
                                        {
                                            "id": "billing",
                                            "title": "Billing Questions",
                                            "description": "Invoices, payments, account queries"
                                        },
                                        {
                                            "id": "installation",
                                            "title": "Installation Support",
                                            "description": "Installation queries and follow-ups"
                                        },
                                        {
                                            "id": "product_info",
                                            "title": "Product Information",
                                            "description": "Solar panels, inverters, batteries"
                                        },
                                        {
                                            "id": "other",
                                            "title": "Other",
                                            "description": "Any other enquiry"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "support_type"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_details",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_details",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Please describe your issue or question in detail:"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "support_details"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_contact",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_contact",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Please provide your preferred contact method:\n"
                               "(Phone number or email address)"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "contact_method"
                }
            },
            "transitions": [
                {
                    "to_step": "confirm_support_request",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # Confirmation step with interactive buttons
        {
            "name": "confirm_support_request",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "Review Support Request"},
                        "body": {
                            "text": "📋 *Support Request Summary*\n\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n"
                                   "📋 *Type:*\n{{support_type}}\n\n"
                                   "📝 *Details:*\n{{support_details}}\n\n"
                                   "📞 *Contact:*\n{{contact_method}}\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                                   "Confirm to submit your support request."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_support", "title": "✅ Confirm"}},
                                {"type": "reply", "reply": {"id": "cancel_support", "title": "❌ Cancel"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "support_confirmation"
                }
            },
            "transitions": [
                {
                    "to_step": "confirmation",
                    "priority": 1,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "confirm_support"
                    }
                },
                {
                    "to_step": "end_cancelled",
                    "priority": 2,
                    "condition_config": {"type": "always_true"}
                }
            ]
        },
        {
            "name": "confirmation",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Thank you for contacting Sungrip Solar Support! ✅\n\n"
                           "We've received your request:\n"
                           "📋 Type: {{support_type}}\n"
                           "📝 Details: {{support_details}}\n"
                           "📞 Contact: {{contact_method}}\n\n"
                           "Our support team will get back to you within 24 hours.\n\n"
                           "For urgent matters, please call us at:\n"
                           "📱 +263 123 456 789\n\n"
                           "Type 'menu' to return to the main menu."
                }
            },
            "transitions": [
                {
                    "to_step": "end",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "end_cancelled",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "❌ Support request cancelled.\n\n"
                           "No worries! If you need help, just type 'support' to start again.\n"
                           "Type 'menu' to return to the main menu."
                }
            },
            "transitions": [
                {
                    "to_step": "end",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "end",
            "type": "end_flow",
            "config": {}
        }
    ]
}
