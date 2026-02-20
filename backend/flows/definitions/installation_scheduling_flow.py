# backend/flows/definitions/installation_scheduling_flow.py

"""
Installation scheduling conversational flow.

Books solar system installation appointments for customers.
Supports WhatsApp interactive flow with a polished legacy fallback
that collects payment preference, booking details, and location.
"""

INSTALLATION_SCHEDULING_FLOW = {
    "name": "installation_scheduling",
    "friendly_name": "Installation Scheduling",
    "description": "Schedules solar system installation appointments",
    "is_active": True,
    "trigger_keywords": ["schedule", "installation", "appointment", "install", "book"],
    "steps": [
        # ── Entry: ensure customer profile exists ──────────────────────
        {
            "name": "ensure_profile",
            "is_entry_point": True,
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "ensure_customer_profile",
                    "parameters": {}
                }]
            },
            "transitions": [
                {
-                    "to_step": "check_whatsapp_flow",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── WhatsApp Flow integration check ────────────────────────────
        {
            "name": "check_whatsapp_flow",
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
                    "to_step": "map_wa_install_fields",
                    "priority": 1,
                    "condition_config": {"type": "whatsapp_flow_response_received"}
                }
            ]
        },
        # ── Map WA field names → conversational field names ──────────
        {
            "name": "map_wa_install_fields",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "map_wa_response",
                    "parameters": {
                        "mappings": {
                            "address": "installation_address",
                            "contact_name": "customer_name"
                        }
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "wa_ask_location_pin",
                    "priority": 1,
                    "condition_config": {
                        "type": "variable_exists",
                        "variable_name": "system_size"
                    }
                },
                {
                    "to_step": "wa_ask_payment",
                    "priority": 2,
                    "condition_config": {"type": "auto"}
                }
            ]
        },
        # ── WA path: ask missing fields ────────────────────────────
        {
            "name": "wa_ask_payment",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "💳 Payment Method"},
                        "body": {
                            "text": "Thanks for submitting the form! Just a couple more details.\n\n"
                                   "How would you like to pay?\n\n"
                                   "💵 *Cash* \u2014 Pay on delivery & installation\n"
                                   "� *3-Month Plan* \u2014 Short-term credit\n"
                                   "📆 *6-Month Plan* \u2014 Spread cost over 6 months"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "cash", "title": "💵 Cash / Full"}},
                                {"type": "reply", "reply": {"id": "installment_3", "title": "🔥 3-Month Plan"}},
                                {"type": "reply", "reply": {"id": "installment_6", "title": "📆 6-Month Plan"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "payment_preference"
                }
            },
            "transitions": [
                {
                    "to_step": "wa_ask_system",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "wa_ask_system",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {
                            "text": "\u26a1 Which system would you like installed?"
                        },
                        "footer": {
                            "text": "Prices in USD \u00b7 Installation included"
                        },
                        "action": {
                            "button": "Select System",
                            "sections": [
                                {
                                    "title": "Available Systems",
                                    "rows": [
                                        {"id": "3.5kva", "title": "\u26a1 3.5 kVA System", "description": "Small home \u00b7 Fridge, TV, lights"},
                                        {"id": "4.2kva", "title": "\u26a1 4.2 kVA System", "description": "Medium home \u00b7 + Cameras, pump"},
                                        {"id": "6.2kva", "title": "\u26a1 6.2 kVA System", "description": "Large home \u00b7 3 fridges, 1.5HP pump"},
                                        {"id": "not_sure", "title": "\ud83e\udd14 Not Sure Yet", "description": "Our team will advise"}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "system_size"
                }
            },
            "transitions": [
                {
                    "to_step": "wa_ask_location_pin",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "wa_ask_location_pin",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📌 Please share your *location pin* so our crew can find you.\n\n"
                               "Tap \ud83d\udcce \u2192 \ud83d\udccd Location \u2192 Send"
                    }
                },
                "reply_config": {
                    "expected_type": "location",
                    "save_to_variable": "location_pin"
                }
            },
            "transitions": [
                {
                    "to_step": "format_install_labels",
                    "condition_config": {"type": "auto"},
                    "priority": 1
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
                    "body": "📅 *Book Your Installation*\n\n"
                           "Great choice! Let's get your solar system "
                           "installation booked. I'll collect a few details "
                           "and our team will confirm within 24 hours.\n\n"
                           "This takes less than 2 minutes ⏱️"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_preferred_date",
                    "priority": 1,
                    "condition_config": {
                        "type": "variable_exists",
                        "variable_name": "system_size"
                    }
                },
                {
                    "to_step": "ask_payment_preference",
                    "priority": 2,
                    "condition_config": {"type": "auto"}
                }
            ]
        },
        # ── Payment preference ─────────────────────────────────────────
        {
            "name": "ask_payment_preference",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "💳 Payment Method"},
                        "body": {
                            "text": "How would you like to pay?\n\n"
                                   "💵 *Cash* — Pay on delivery & installation\n"
                                   "� *3-Month Plan* — Short-term credit\n"
                                   "📆 *6-Month Plan* — Spread cost over 6 months"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "cash", "title": "💵 Cash / Full"}},
                                {"type": "reply", "reply": {"id": "installment_3", "title": "🔥 3-Month Plan"}},
                                {"type": "reply", "reply": {"id": "installment_6", "title": "📆 6-Month Plan"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "payment_preference"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_system_size",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── System size selection ──────────────────────────────────────
        {
            "name": "ask_system_size",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {
                            "text": "⚡ Which system would you like installed?\n\n"
                                   "Select the size that matches your household needs."
                        },
                        "footer": {
                            "text": "Prices in USD · Installation included"
                        },
                        "action": {
                            "button": "Select System",
                            "sections": [
                                {
                                    "title": "Available Systems",
                                    "rows": [
                                        {
                                            "id": "3.5kva",
                                            "title": "⚡ 3.5 kVA System",
                                            "description": "Small home · Fridge, TV, lights, 0.5HP pump"
                                        },
                                        {
                                            "id": "4.2kva",
                                            "title": "⚡ 4.2 kVA System",
                                            "description": "Medium home · + Cameras, 0.75HP pump"
                                        },
                                        {
                                            "id": "6.2kva",
                                            "title": "⚡ 6.2 kVA System",
                                            "description": "Large home · 3 fridges, 1.5HP pump"
                                        },
                                        {
                                            "id": "not_sure",
                                            "title": "🤔 Not Sure Yet",
                                            "description": "Our team will advise on site"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "system_size"
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
        # ── Date & time ────────────────────────────────────────────────
        {
            "name": "ask_preferred_date",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📅 When would you like the installation?\n\n"
                               "_e.g. Monday, Next week, 15 March_"
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
                            "text": "🕐 What time of day works best?"
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
        # ── Address & location ─────────────────────────────────────────
        {
            "name": "ask_installation_address",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "🏠 Please provide the *full installation address*:\n\n"
                               "_e.g. 42 Solar Drive, Borrowdale, Harare_\n\n"
                               "ℹ️ Outside Harare — transport charges may apply."
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
        {
            "name": "ask_location_pin",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📌 Please share your *location pin* so our crew can find you.\n\n"
                               "Tap 📎 → 📍 Location → Send"
                    }
                },
                "reply_config": {
                    "expected_type": "location",
                    "save_to_variable": "location_pin"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_additional_notes",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Optional notes ─────────────────────────────────────────────
        {
            "name": "ask_additional_notes",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "📝 Any additional notes for the installation team?\n\n"
                                   "_e.g. Gate access, roof type, special requirements_"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "no_notes", "title": "➡️ Skip"}},
                                {"type": "reply", "reply": {"id": "add_notes", "title": "📝 Add Notes"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "notes_choice"
                }
            },
            "transitions": [
                {
                    "to_step": "collect_notes",
                    "priority": 1,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "add_notes"
                    }
                },
                {
                    "to_step": "format_install_labels",
                    "priority": 2,
                    "condition_config": {"type": "always_true"}
                }
            ]
        },
        {
            "name": "collect_notes",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📝 Type your notes below:"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "additional_notes"
                }
            },
            "transitions": [
                {
                    "to_step": "format_install_labels",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },        # ── Format raw IDs to readable labels ──────────────────────
        {
            "name": "format_install_labels",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "format_labels",
                    "parameters": {
                        "variables": ["payment_preference", "system_size", "time_preference"]
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "confirm_installation",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },        # ── Confirmation ───────────────────────────────────────────────
        {
            "name": "confirm_installation",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "📋 Booking Summary"},
                        "body": {
                            "text": "Hi {{customer_name}}, please review your booking:\n\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n"
                                   "⚡ *System:* {{system_size}}\n"
                                   "💳 *Payment:* {{payment_preference}}\n"
                                   "📅 *Date:* {{preferred_date}}\n"
                                   "🕐 *Time:* {{time_preference}}\n"
                                   "🏠 *Address:* {{installation_address}}\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                                   "Tap *Confirm* to submit or *Edit* to start over."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_install", "title": "✅ Confirm"}},
                                {"type": "reply", "reply": {"id": "edit_install", "title": "✏️ Edit"}},
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
                    "to_step": "fallback_welcome",
                    "priority": 2,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "edit_install"
                    }
                },
                {
                    "to_step": "end_cancelled",
                    "priority": 3,
                    "condition_config": {"type": "always_true"}
                }
            ]
        },
        # ── Success ────────────────────────────────────────────────────
        {
            "name": "confirm_scheduling",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "✅ *Installation Booked!*\n\n"
                           "Thank you, {{customer_name}}! Here's your booking:\n\n"
                           "⚡ System: {{system_size}}\n"
                           "💳 Payment: {{payment_preference}}\n"
                           "📅 Date: {{preferred_date}}\n"
                           "🕐 Time: {{time_preference}}\n"
                           "🏠 Address: {{installation_address}}\n\n"
                           "Our installation team will call you within *24 hours* "
                           "to confirm the exact schedule.\n\n"
                           "📞 WhatsApp: 0782 233 111 / 0777 139 159\n\n"
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
                    "body": "❌ *Booking cancelled.*\n\n"
                           "No worries! You can reschedule anytime by typing *schedule*.\n"
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
