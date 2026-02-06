"""
Solar quote request flow definition.

This flow guides customers through the process of requesting a solar system quote.
"""

SOLAR_QUOTE_FLOW = {
    "name": "solar_quote_request",
    "friendly_name": "Solar Quote Request",
    "description": "Guides customers through solar system quote request process",
    "is_active": True,
    "trigger_keywords": ["quote", "price", "how much", "cost", "solar system"],
    "steps": [
        {
            "name": "welcome",
            "step_type": "send_message",
            "is_entry_point": True,
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
            "step_type": "question",
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
                    "context_variable": "monthly_bill"
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
            "step_type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "What type of roof do you have? (e.g., tile, metal, asbestos, concrete)"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "context_variable": "roof_type"
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
            "step_type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "What is your location/city?"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "context_variable": "location"
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
            "step_type": "action",
            "config": {
                "action_type": "update_context",
                "parameters": {
                    "estimated_system_size": 5.0,  # This would be calculated based on monthly_bill
                    "estimated_cost": 5000.0  # This would be calculated
                }
            },
            "transitions": [
                {
                    "to_step": "provide_quote",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "provide_quote",
            "step_type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Based on your monthly bill of ${{monthly_bill}}, I recommend a solar system.\n\n"
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
            "name": "end",
            "step_type": "end_flow",
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
        {
            "name": "welcome",
            "step_type": "send_message",
            "is_entry_point": True,
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
            "step_type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "What date would you prefer for the installation? (e.g., Monday, Next Week, etc.)"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "context_variable": "preferred_date"
                }
            },
            "transitions": [
                {
                    "to_step": "confirm_scheduling",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "confirm_scheduling",
            "step_type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Thank you! I've noted your preference for {{preferred_date}}. "
                           "Our installation team will contact you within 24 hours to confirm the exact time."
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
            "step_type": "end_flow",
            "config": {}
        }
    ]
}
