# backend/flows/definitions/solar_packages_flow.py

"""
Solar packages flow definition.

Displays available solar system packages and optionally routes to
the quote request flow for interested customers.

NOTE: Package details and pricing are currently hardcoded in the message.
For production, consider implementing a webhook action to fetch package data
dynamically from the SolarPackage model to ensure accuracy when prices change.
"""

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
                "message": "Excellent! Let me get some details for your quote. 📋",
                "initial_context_template": {
                    "package_interest": "{{package_interest}}"
                }
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
