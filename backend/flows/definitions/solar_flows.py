"""
Solar quote request flow definitions.

This module contains all conversational flow definitions for Sungrip Solar chatbot.
Includes main menu, quote request, installation scheduling, solar packages, and support flows.
"""

# Main Menu Flow - Entry point for users
MAIN_MENU_FLOW = {
    "name": "main_menu",
    "friendly_name": "Main Menu",
    "description": "Main menu for Sungrip Solar chatbot - presents users with service options",
    "is_active": True,
    "trigger_keywords": ["menu", "start", "hello", "hi", "help", "options"],
    "steps": [
        {
            "name": "welcome",
            "type": "send_message",
            "is_entry_point": True,
            "config": {
                "message_type": "text",
                "text": {
                    "body": "🌞 Welcome to Sungrip Solar! ☀️\n\n"
                           "We're here to help you with solar energy solutions. "
                           "How can we assist you today?\n\n"
                           "Please select an option:\n"
                           "1️⃣ Request a Quote\n"
                           "2️⃣ Schedule Installation\n"
                           "3️⃣ View Solar Packages\n"
                           "4️⃣ Contact Support\n\n"
                           "Reply with the number of your choice (1-4)."
                }
            },
            "transitions": [
                {
                    "to_step": "handle_choice",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "handle_choice",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Please enter your choice (1-4):"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "menu_choice"
                }
            },
            "transitions": [
                {
                    "to_step": "route_to_quote",
                    "condition_config": {
                        "type": "expression",
                        "expression": "menu_choice in ['1', 'quote', 'request quote']"
                    },
                    "priority": 1
                },
                {
                    "to_step": "route_to_installation",
                    "condition_config": {
                        "type": "expression",
                        "expression": "menu_choice in ['2', 'schedule', 'installation']"
                    },
                    "priority": 2
                },
                {
                    "to_step": "route_to_packages",
                    "condition_config": {
                        "type": "expression",
                        "expression": "menu_choice in ['3', 'packages', 'view packages']"
                    },
                    "priority": 3
                },
                {
                    "to_step": "route_to_support",
                    "condition_config": {
                        "type": "expression",
                        "expression": "menu_choice in ['4', 'support', 'help']"
                    },
                    "priority": 4
                },
                {
                    "to_step": "invalid_choice",
                    "condition_config": {"type": "auto"},
                    "priority": 5
                }
            ]
        },
        {
            "name": "route_to_quote",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "solar_quote_request",
                "message": "Great! Let me help you get a quote. 📋"
            },
            "transitions": []
        },
        {
            "name": "route_to_installation",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "installation_scheduling",
                "message": "Perfect! Let's schedule your installation. 📅"
            },
            "transitions": []
        },
        {
            "name": "route_to_packages",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "solar_packages",
                "message": "Let me show you our available solar packages. 📦"
            },
            "transitions": []
        },
        {
            "name": "route_to_support",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "contact_support",
                "message": "I'll connect you with our support team. 👥"
            },
            "transitions": []
        },
        {
            "name": "invalid_choice",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "I'm sorry, I didn't understand that. Please reply with a number from 1 to 4."
                }
            },
            "transitions": [
                {
                    "to_step": "handle_choice",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        }
    ]
}


# Solar Quote Request Flow
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


# Solar Packages Flow - Display available packages
# NOTE: Package details and pricing are currently hardcoded in the message.
# For production, consider implementing a webhook action to fetch package data
# dynamically from the SolarPackage model to ensure accuracy when prices change.
SOLAR_PACKAGES_FLOW = {
    "name": "solar_packages",
    "friendly_name": "Solar Packages",
    "description": "Displays available solar system packages to customers",
    "is_active": True,
    "trigger_keywords": ["packages", "systems", "options", "what do you have"],
    "steps": [
        {
            "name": "welcome",
            "type": "send_message",
            "is_entry_point": True,
            "config": {
                "message_type": "text",
                "text": {
                    "body": "☀️ Sungrip Solar Packages ☀️\n\n"
                           "We offer various solar packages to meet your needs:\n\n"
                           "📦 SMALL HOME PACKAGE (1-2 Bedrooms)\n"
                           "• 3kW Solar System\n"
                           "• 8 x 375W Solar Panels\n"
                           "• 3kW Inverter\n"
                           "• Installation Included\n"
                           "💰 Price: $3,500\n\n"
                           "📦 MEDIUM HOME PACKAGE (3-4 Bedrooms)\n"
                           "• 5kW Solar System\n"
                           "• 14 x 375W Solar Panels\n"
                           "• 5kW Inverter\n"
                           "• Installation Included\n"
                           "💰 Price: $5,500\n\n"
                           "📦 LARGE HOME PACKAGE (5+ Bedrooms)\n"
                           "• 8kW Solar System\n"
                           "• 22 x 375W Solar Panels\n"
                           "• 8kW Inverter\n"
                           "• Installation Included\n"
                           "💰 Price: $8,500\n\n"
                           "📦 SMALL BUSINESS PACKAGE\n"
                           "• 10kW Solar System\n"
                           "• 27 x 375W Solar Panels\n"
                           "• 10kW Inverter\n"
                           "• Installation Included\n"
                           "💰 Price: $10,500\n\n"
                           "Would you like more information about any of these packages?"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_interest",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_interest",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Which package interests you? (Reply: Small, Medium, Large, Business, or None)"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "package_interest"
                }
            },
            "transitions": [
                {
                    "to_step": "provide_details",
                    "condition_config": {
                        "type": "expression",
                        "expression": "package_interest.lower() not in ['none', 'no', 'nothing']"
                    },
                    "priority": 1
                },
                {
                    "to_step": "thank_you",
                    "condition_config": {"type": "auto"},
                    "priority": 2
                }
            ]
        },
        {
            "name": "provide_details",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Great choice! 🎉\n\n"
                           "The {{package_interest}} package is excellent for your needs.\n\n"
                           "All our packages include:\n"
                           "✅ Professional Installation\n"
                           "✅ 25-Year Panel Warranty\n"
                           "✅ 5-Year Inverter Warranty\n"
                           "✅ Free System Monitoring\n"
                           "✅ Lifetime Technical Support\n\n"
                           "Would you like to request a formal quote? (Reply: Yes or No)"
                }
            },
            "transitions": [
                {
                    "to_step": "route_to_quote",
                    "condition_config": {
                        "type": "auto"
                    },
                    "priority": 1
                }
            ]
        },
        {
            "name": "route_to_quote",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Would you like to request a formal quote?"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "wants_quote"
                }
            },
            "transitions": [
                {
                    "to_step": "switch_to_quote",
                    "condition_config": {
                        "type": "expression",
                        "expression": "wants_quote.lower() in ['yes', 'y', 'sure', 'ok']"
                    },
                    "priority": 1
                },
                {
                    "to_step": "thank_you",
                    "condition_config": {"type": "auto"},
                    "priority": 2
                }
            ]
        },
        {
            "name": "switch_to_quote",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "solar_quote_request",
                "message": "Excellent! Let me get some details for your quote. 📋"
            },
            "transitions": []
        },
        {
            "name": "thank_you",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Thank you for your interest in Sungrip Solar! 🌞\n\n"
                           "If you have any questions, feel free to contact us anytime.\n"
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


# Contact Support Flow
CONTACT_SUPPORT_FLOW = {
    "name": "contact_support",
    "friendly_name": "Contact Support",
    "description": "Connect customers with support team and collect their inquiry",
    "is_active": True,
    "trigger_keywords": ["support", "help", "contact", "talk to human", "agent"],
    "steps": [
        {
            "name": "welcome",
            "type": "send_message",
            "is_entry_point": True,
            "config": {
                "message_type": "text",
                "text": {
                    "body": "👋 Sungrip Solar Support\n\n"
                           "Our support team is here to help you!\n\n"
                           "Please select what you need help with:\n"
                           "1️⃣ Technical Issues\n"
                           "2️⃣ Billing Questions\n"
                           "3️⃣ Installation Support\n"
                           "4️⃣ Product Information\n"
                           "5️⃣ Other\n\n"
                           "Reply with the number (1-5)."
                }
            },
            "transitions": [
                {
                    "to_step": "ask_support_type",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_support_type",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Please enter your choice (1-5):"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
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
