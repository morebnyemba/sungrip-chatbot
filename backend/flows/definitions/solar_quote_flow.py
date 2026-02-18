# backend/flows/definitions/solar_quote_flow.py

"""
Solar quote request flow definition.

Guides customers through the process of requesting a solar system quote.
Supports WhatsApp interactive flow with legacy message-based fallback.
"""

SOLAR_QUOTE_FLOW = {
    "name": "solar_quote_request",
    "friendly_name": "Solar Quote Request",
    "description": "Guides customers through solar system quote request process",
    "is_active": True,
    "trigger_keywords": ["quote", "price", "how much", "cost", "solar system"],
    "steps": [
        # WhatsApp Flow integration entry point
        {
            "name": "check_whatsapp_flow",
            "is_entry_point": True,
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "check_whatsapp_flow",
                    "parameters": {
                        "flow_name": "solar_quote_whatsapp",
                        "save_to_variable": "wa_flow_data"
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "send_whatsapp_flow",
                    "priority": 1,
                    "condition_config": {
                        "type": "variable_exists",
                        "variable_name": "wa_flow_data"
                    }
                },
                {
                    "to_step": "fallback_welcome",
                    "priority": 2,
                    "condition_config": {"type": "always_true"}
                }
            ]
        },
        # WhatsApp Flow path
        {
            "name": "send_whatsapp_flow",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "send_whatsapp_flow",
                    "parameters": {
                        "flow_variable": "wa_flow_data"
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "wait_for_whatsapp_response",
                    "priority": 1,
                    "condition_config": {"type": "always_true"}
                }
            ]
        },
        {
            "name": "wait_for_whatsapp_response",
            "type": "action",
            "config": {
                "actions_to_run": [],
                "wait_for": "whatsapp_flow_response"
            },
            "transitions": [
                {
                    "to_step": "provide_quote",
                    "priority": 1,
                    "condition_config": {"type": "whatsapp_flow_response_received"}
                }
            ]
        },
        # Legacy message-based flow path
        {
            "name": "fallback_welcome",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Hello! I can help you get a quote for a solar system from Sungrip Solar. "
                           "I'll need to ask you a few questions to provide an accurate quote."
                }
            },
            "transitions": [
                {
                    "to_step": "ask_monthly_bill",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_monthly_bill",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "What is your average monthly electricity bill in USD?"
                    }
                },
                "reply_config": {
                    "expected_type": "number",
                    "validation": {"min": 0, "max": 100000},
                    "save_to_variable": "monthly_bill"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_roof_type",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_roof_type",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "What type of roof do you have? (e.g., tile, metal, asbestos, concrete)"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "roof_type"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_location",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_location",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "What is your location/city?"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "location"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_location_pin",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # Location picker step
        {
            "name": "ask_location_pin",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Please send your location by using WhatsApp's location feature "
                               "(📍 Location button). This helps our team find your site easily."
                    }
                },
                "reply_config": {
                    "expected_type": "location",
                    "save_to_variable": "location_pin"
                }
            },
            "transitions": [
                {
                    "to_step": "calculate_quote",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "calculate_quote",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "update_context",
                    "parameters": {
                        "estimated_system_size": 5.0,
                        "estimated_cost": 5000.0
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "confirm_quote_request",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # Confirmation step with interactive buttons
        {
            "name": "confirm_quote_request",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "Review Quote Request"},
                        "body": {
                            "text": "📋 *Solar Quote Request*\n\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n"
                                   "💰 *Monthly Bill:*\n${{monthly_bill}}\n\n"
                                   "🏠 *Roof Type:*\n{{roof_type}}\n\n"
                                   "📍 *Location:*\n{{location}}\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                                   "Confirm to submit your quote request."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_quote", "title": "✅ Confirm"}},
                                {"type": "reply", "reply": {"id": "cancel_quote", "title": "❌ Cancel"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "quote_confirmation"
                }
            },
            "transitions": [
                {
                    "to_step": "provide_quote",
                    "priority": 1,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "confirm_quote"
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
            "name": "provide_quote",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "✅ Quote request submitted!\n\n"
                           "Based on your monthly bill of ${{monthly_bill}}, I recommend a solar system.\n\n"
                           "📍 Location: {{location}}\n"
                           "🏠 Roof Type: {{roof_type}}\n\n"
                           "Our sales team will contact you shortly with a detailed quote. "
                           "Is there anything else you'd like to know?"
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
                    "body": "❌ Quote request cancelled.\n\n"
                           "No worries! If you change your mind, just type 'quote' to start again.\n"
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
