# backend/flows/definitions/installation_scheduling_flow.py

"""
Installation scheduling flow definition.

Schedules solar system installation appointments for customers.
Supports WhatsApp interactive flow with legacy message-based fallback.
"""

INSTALLATION_SCHEDULING_FLOW = {
    "name": "installation_scheduling",
    "friendly_name": "Installation Scheduling",
    "description": "Schedules solar system installation appointments",
    "is_active": True,
    "trigger_keywords": ["schedule", "installation", "appointment", "install"],
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
                        "flow_name": "installation_scheduling_whatsapp",
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
                    "to_step": "confirm_scheduling",
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
                    "body": "I can help you schedule your solar system installation. "
                           "Let me check available dates for you."
                }
            },
            "transitions": [
                {
                    "to_step": "ask_preferred_date",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_preferred_date",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "What date would you prefer for the installation? (e.g., Monday, Next Week, etc.)"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "preferred_date"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_time_preference",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_time_preference",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "What time of day works best for the installation?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "morning", "title": "🌅 Morning"}},
                                {"type": "reply", "reply": {"id": "afternoon", "title": "🌇 Afternoon"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "time_preference"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_installation_address",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_installation_address",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Please provide your installation address:"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "installation_address"
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
                    "to_step": "confirm_installation",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # Confirmation step with interactive buttons
        {
            "name": "confirm_installation",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "Review Installation Request"},
                        "body": {
                            "text": "📋 *Installation Scheduling*\n\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n"
                                   "📅 *Preferred Date:*\n{{preferred_date}}\n\n"
                                   "🕐 *Time Preference:*\n{{time_preference}}\n\n"
                                   "🏠 *Address:*\n{{installation_address}}\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                                   "Confirm to submit your installation request."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_install", "title": "✅ Confirm"}},
                                {"type": "reply", "reply": {"id": "cancel_install", "title": "❌ Cancel"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "install_confirmation"
                }
            },
            "transitions": [
                {
                    "to_step": "confirm_scheduling",
                    "priority": 1,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "confirm_install"
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
            "name": "confirm_scheduling",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "✅ Installation request submitted!\n\n"
                           "Thank you! I've noted your preference for {{preferred_date}} ({{time_preference}}).\n"
                           "📍 Address: {{installation_address}}\n\n"
                           "Our installation team will contact you within 24 hours to confirm the exact time.\n\n"
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
                    "body": "❌ Installation request cancelled.\n\n"
                           "No worries! If you change your mind, just type 'schedule' to start again.\n"
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
