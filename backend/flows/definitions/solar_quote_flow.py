# backend/flows/definitions/solar_quote_flow.py

"""
Solar quote request conversational flow.

Guides customers through requesting a solar system quote.
Supports WhatsApp interactive flow with a polished legacy fallback
that uses interactive lists / buttons wherever possible.
"""

SOLAR_QUOTE_FLOW = {
    "name": "solar_quote_request",
    "friendly_name": "Solar Quote Request",
    "description": "Guides customers through the solar system quote request process",
    "is_active": True,
    "trigger_keywords": ["quote", "price", "how much", "cost", "solar system"],
    "steps": [
        # ── WhatsApp Flow integration entry point ──────────────────────
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
        # ── WhatsApp Flow path ─────────────────────────────────────────
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
        # ── Legacy conversational fallback ─────────────────────────────
        {
            "name": "fallback_welcome",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "📋 *Solar Quote Request*\n\n"
                           "Great choice! I'll walk you through a few quick questions "
                           "to build you a personalised solar system quote.\n\n"
                           "This takes less than 2 minutes ⏱️"
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
                        "body": "💰 What is your *average monthly electricity bill* in USD?\n\n"
                               "_e.g. 150_"
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
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {
                            "text": "🏠 What type of roof do you have?\n\n"
                                   "This helps us determine the best mounting system for your solar panels."
                        },
                        "footer": {
                            "text": "Select your roof type"
                        },
                        "action": {
                            "button": "Select Roof Type",
                            "sections": [
                                {
                                    "title": "Roof Types",
                                    "rows": [
                                        {"id": "tile", "title": "Tile Roof", "description": "Clay or concrete tiles"},
                                        {"id": "metal", "title": "Metal / IBR", "description": "Corrugated iron or metal sheets"},
                                        {"id": "asbestos", "title": "Asbestos", "description": "Asbestos cement sheets"},
                                        {"id": "concrete", "title": "Flat Concrete", "description": "Flat concrete slab roof"},
                                        {"id": "other", "title": "Other", "description": "Thatch, shingle, or other"}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "roof_type"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_property_type",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_property_type",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "🏘️ What best describes your property?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "residential", "title": "🏠 Residential"}},
                                {"type": "reply", "reply": {"id": "commercial", "title": "🏢 Commercial"}},
                                {"type": "reply", "reply": {"id": "industrial", "title": "🏭 Industrial"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "property_type"
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
                        "body": "📍 What city or town are you located in?\n\n"
                               "_e.g. Harare, Bulawayo, Mutare_"
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
        {
            "name": "ask_location_pin",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📌 Please share your *location pin* using WhatsApp's location feature.\n\n"
                               "Tap the 📎 (attach) button → 📍 Location → Send.\n\n"
                               "This helps our team plan the site assessment."
                    }
                },
                "reply_config": {
                    "expected_type": "location",
                    "save_to_variable": "location_pin"
                }
            },
            "transitions": [
                {
                    "to_step": "confirm_quote_request",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Confirmation with interactive buttons ──────────────────────
        {
            "name": "confirm_quote_request",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "📋 Review Quote Request"},
                        "body": {
                            "text": "Please confirm the details below:\n\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n"
                                   "💰 *Monthly Bill:* ${{monthly_bill}}\n"
                                   "🏠 *Roof Type:* {{roof_type}}\n"
                                   "🏘️ *Property:* {{property_type}}\n"
                                   "📍 *Location:* {{location}}\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                                   "Tap *Confirm* to submit your request."
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
        # ── Success & closing ──────────────────────────────────────────
        {
            "name": "provide_quote",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "✅ *Quote request submitted!*\n\n"
                           "Thank you, {{customer_name}}! Here's a summary:\n\n"
                           "💰 Monthly bill: ${{monthly_bill}}\n"
                           "🏠 Roof: {{roof_type}}\n"
                           "📍 Location: {{location}}\n\n"
                           "Our solar consultant will contact you within "
                           "*24 hours* with a detailed, personalised quote.\n\n"
                           "📞 Need it sooner? Call us at *+263 123 456 789*\n\n"
                           "Type *menu* to return to the main menu."
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
                    "body": "❌ *Quote request cancelled.*\n\n"
                           "No worries! You can start again anytime by typing *quote*.\n"
                           "Type *menu* to return to the main menu."
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
