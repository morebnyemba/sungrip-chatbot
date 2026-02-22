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
                            "text": "☀️ Sungrip Solar"
                        },
                        "body": {
                            "text": "Hi {{customer_name}}, welcome to *Sungrip Solar* — "
                                   "Zimbabwe's trusted solar energy partner.\n\n"
                                   "🔋 *What we offer:*\n"
                                   "1️⃣ Solar systems on credit — pay a small deposit after fix & supply, "
                                   "delivery and installation included. Use now, pay later while your "
                                   "business runs, your life runs!\n"
                                   "2️⃣ Solar systems with warranty agreements and receipts\n"
                                   "3️⃣ One year after-service support\n"
                                   "4️⃣ Free quotations & consultations for bigger solar systems "
                                   "(6.2 kVA+ up to solar farms)\n\n"
                                   "Tap the button below to explore our services 👇"
                        },
                        "footer": {
                            "text": "Powered by slykertech.co.zw"
                        },
                        "action": {
                            "button": "📋 View Options",
                            "sections": [
                                {
                                    "title": "Solar Solutions",
                                    "rows": [
                                        {
                                            "id": "view_packages",
                                            "title": "🔆 Solar Packages",
                                            "description": "Compare our ready-made solar packages & pricing"
                                        },
                                        {
                                            "id": "shop_products",
                                            "title": "🛒 Shop Products",
                                            "description": "Browse individual solar equipment & accessories"
                                        },
                                        {
                                            "id": "request_quote",
                                            "title": "📋 Get a Free Quote",
                                            "description": "Custom solar system? We'll size one just for you"
                                        },
                                        {
                                            "id": "schedule_installation",
                                            "title": "📅 Book Installation",
                                            "description": "Choose a convenient date for your setup"
                                        }
                                    ]
                                },
                                {
                                    "title": "Help & Support",
                                    "rows": [
                                        {
                                            "id": "contact_support",
                                            "title": "💬 Contact Support",
                                            "description": "Speak to our team for any enquiry"
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
                    "to_step": "route_to_packages",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "view_packages"
                    },
                    "priority": 1
                },
                {
                    "to_step": "route_to_catalog",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "shop_products"
                    },
                    "priority": 2
                },
                {
                    "to_step": "route_to_quote",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "request_quote"
                    },
                    "priority": 3
                },
                {
                    "to_step": "route_to_installation",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "schedule_installation"
                    },
                    "priority": 4
                },
                {
                    "to_step": "route_to_support",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "contact_support"
                    },
                    "priority": 5
                },
                {
                    "to_step": "show_main_menu",
                    "condition_config": {"type": "always_true"},
                    "priority": 6
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
            "name": "route_to_catalog",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "send_catalog_message",
                        "params_template": {
                            "body_text": "🛒 *Sungrip Solar Product Catalog*\n\nBrowse our products below. Add items to your cart and tap *Send* to place your order — we'll confirm it right here on WhatsApp!",
                            "footer_text": "Tap on a product to view details"
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "end_after_catalog",
                    "condition_config": {"type": "always_true"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "end_after_catalog",
            "type": "end_flow",
            "config": {},
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
