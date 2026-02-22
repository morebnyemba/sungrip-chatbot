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
                    "to_step": "check_whatsapp_flow",
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
                        "variable_name": "package_name"
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
                    "save_to_variable": "package_payment_label"
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
                    "save_to_variable": "package_name"
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
                    "body": "📅 *Book Your Solar Installation*\n\n"
                           "We install solar systems for *homes, businesses & farms* "
                           "across Zimbabwe.\n\n"
                           "✅ Payment after delivery & installation (Supply & Fix)\n"
                           "✅ 3 investment options: Cash, 3-month & 6-month plans\n\n"
                           "Let me show you our available packages so you can pick "
                           "the right one — this takes less than 2 minutes ⏱️"
                }
            },
            "transitions": [
                {
                    "to_step": "build_packages_list",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Build dynamic packages list from DB ────────────────────────
        {
            "name": "build_packages_list",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "build_packages_interactive_list",
                        "parameters": {}
                    },
                    {
                        "action_type": "send_dynamic_message",
                        "parameters": {
                            "message_variable": "_packages_list_msg"
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "capture_package_selection",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Capture package selection ──────────────────────────────────
        {
            "name": "capture_package_selection",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "👆 Tap *View Packages* above to browse, then select the package you'd like installed."
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "selected_package"
                }
            },
            "transitions": [
                {
                    "to_step": "load_package_details",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Load full package details ──────────────────────────────────
        {
            "name": "load_package_details",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "fetch_package_details",
                        "parameters": {
                            "selection_variable": "selected_package"
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "show_package_and_proceed",
                    "condition_config": {
                        "type": "expression",
                        "expression": "package_found == True"
                    },
                    "priority": 1
                },
                {
                    "to_step": "build_packages_list",
                    "condition_config": {"type": "always_true"},
                    "priority": 2
                }
            ]
        },
        # ── Show package details + payment options ─────────────────────
        {
            "name": "show_package_and_proceed",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "{{package_detail_text}}\n\n"
                           "━━━━━━━━━━━━━━━━━━━━\n"
                           "💳 *3 Investment Options:*\n"
                           "  1️⃣ *Cash Price* — Pay in full & save\n"
                           "  2️⃣ *3-Month Pay Plan* — Spread over 3 months\n"
                           "  3️⃣ *6-Month Pay Plan* — Spread over 6 months\n\n"
                           "✅ *Payment after delivery & installation*\n"
                           "   (Supply & Fix — we deliver, install, then you pay)\n"
                           "━━━━━━━━━━━━━━━━━━━━"
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
                        "variables": ["time_preference"]
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
                                   "📦 *Package:* {{package_name}}\n"
                                   "💳 *Payment:* {{package_payment_label}}\n"
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
                    "to_step": "save_and_notify_install",
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
        # ── Save to DB & notify team ──────────────────────────────────
        {
            "name": "save_and_notify_install",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "save_installation_request",
                        "parameters": {}
                    },
                    {
                        "action_type": "send_group_notification",
                        "parameters": {
                            "template_name": "sungrip_new_installation_request",
                            "group_names": ["Sales Team"]
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "confirm_scheduling",
                    "condition_config": {"type": "auto"},
                    "priority": 1
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
                           "📦 Package: {{package_name}}\n"
                           "💳 Payment: {{package_payment_label}}\n"
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
