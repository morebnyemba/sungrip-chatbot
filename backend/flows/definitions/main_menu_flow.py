# backend/flows/definitions/main_menu_flow.py

"""
Main menu flow definition for Sungrip Solar chatbot.

This is the entry point flow that greets users and routes them to the
appropriate sub-flow via WhatsApp interactive list messages.
Follows the architecture pattern from morebnyemba/hanna.
"""

MAIN_MENU_FLOW = {
    "name": "main_menu",
    "friendly_name": "Main Menu",
    "description": "Main menu for Sungrip Solar chatbot - presents users with service options via interactive list",
    "is_active": True,
    "trigger_keywords": ["menu", "start", "hello", "hi", "help", "options"],
    "steps": [
        # Step 1: Ensure customer profile exists (action entry point)
        {
            "name": "ensure_customer_profile_exists",
            "type": "action",
            "is_entry_point": True,
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "ensure_customer_profile",
                        "parameters": {}
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "show_main_menu",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # Step 2: Show interactive list menu with personalised greeting
        {
            "name": "show_main_menu",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {
                            "type": "text",
                            "text": "Sungrip Solar"
                        },
                        "body": {
                            "text": "🌞 Hello {{customer_name}}! Welcome to Sungrip Solar ☀️\n\n"
                                   "We provide reliable solar energy solutions "
                                   "for homes and businesses across Zimbabwe.\n\n"
                                   "How can we help you today?"
                        },
                        "footer": {
                            "text": "Select an option below"
                        },
                        "action": {
                            "button": "View Options",
                            "sections": [
                                {
                                    "title": "Our Services",
                                    "rows": [
                                        {
                                            "id": "request_quote",
                                            "title": "Request a Quote",
                                            "description": "Get a personalized solar system quote"
                                        },
                                        {
                                            "id": "schedule_installation",
                                            "title": "Schedule Installation",
                                            "description": "Book your solar panel installation"
                                        },
                                        {
                                            "id": "view_packages",
                                            "title": "View Solar Packages",
                                            "description": "Browse our solar package options"
                                        }
                                    ]
                                },
                                {
                                    "title": "Support",
                                    "rows": [
                                        {
                                            "id": "contact_support",
                                            "title": "Contact Support",
                                            "description": "Get help from our support team"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "menu_choice"
                }
            },
            "transitions": [
                {
                    "to_step": "route_to_quote",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "request_quote"
                    },
                    "priority": 1
                },
                {
                    "to_step": "route_to_installation",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "schedule_installation"
                    },
                    "priority": 2
                },
                {
                    "to_step": "route_to_packages",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "view_packages"
                    },
                    "priority": 3
                },
                {
                    "to_step": "route_to_support",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "contact_support"
                    },
                    "priority": 4
                },
                {
                    "to_step": "show_main_menu",
                    "condition_config": {"type": "always_true"},
                    "priority": 5
                }
            ]
        },
        # Route steps - switch to sub-flows
        {
            "name": "route_to_quote",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "solar_quote_request",
                "message": "Great! Let me help you get a quote. 📋",
                "initial_context_template": {}
            },
            "transitions": []
        },
        {
            "name": "route_to_installation",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "installation_scheduling",
                "message": "Perfect! Let's schedule your installation. 📅",
                "initial_context_template": {}
            },
            "transitions": []
        },
        {
            "name": "route_to_packages",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "solar_packages",
                "message": "Let me show you our available solar packages. 📦",
                "initial_context_template": {}
            },
            "transitions": []
        },
        {
            "name": "route_to_support",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "contact_support",
                "message": "I'll connect you with our support team. 👥",
                "initial_context_template": {}
            },
            "transitions": []
        }
    ]
}
