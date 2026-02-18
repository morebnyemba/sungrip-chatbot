# backend/flows/definitions/solar_packages_flow.py

"""
Solar packages flow definition.

Displays available solar system packages and optionally routes to
the quote request flow for interested customers.

Package data is loaded dynamically from the SolarPackage model via the
``fetch_solar_packages`` action so that pricing, features, and availability
are always up to date and admin-configurable.
"""

SOLAR_PACKAGES_FLOW = {
    "name": "solar_packages",
    "friendly_name": "Solar Packages",
    "description": "Displays available solar system packages to customers (DB-driven)",
    "is_active": True,
    "trigger_keywords": ["packages", "systems", "options", "what do you have"],
    "steps": [
        # Step 1: Fetch packages from the database
        {
            "name": "fetch_packages",
            "type": "action",
            "is_entry_point": True,
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "fetch_solar_packages",
                        "parameters": {
                            "save_to_variable": "packages_text"
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "show_packages",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # Step 2: Display packages and ask for interest
        {
            "name": "show_packages",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "{{packages_text}}\n\n"
                           "All our packages include:\n"
                           "✅ Professional Installation\n"
                           "✅ 25-Year Panel Warranty\n"
                           "✅ 5-Year Inverter Warranty\n"
                           "✅ Free System Monitoring\n"
                           "✅ Lifetime Technical Support"
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
        # Step 3: Ask if they'd like a quote (interactive buttons)
        {
            "name": "ask_interest",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "Would you like to request a formal quote for one of these packages?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "yes_quote", "title": "📋 Get a Quote"}},
                                {"type": "reply", "reply": {"id": "back_menu", "title": "🏠 Main Menu"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "package_action"
                }
            },
            "transitions": [
                {
                    "to_step": "switch_to_quote",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "yes_quote"
                    },
                    "priority": 1
                },
                {
                    "to_step": "thank_you",
                    "condition_config": {"type": "always_true"},
                    "priority": 2
                }
            ]
        },
        {
            "name": "switch_to_quote",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "solar_quote_request",
                "message": "Excellent! Let me get some details for your quote. 📋",
                "initial_context_template": {}
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
