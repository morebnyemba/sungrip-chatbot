"""
Main menu, package viewing, and assessment booking flows for Sungrip Solar.

These flows provide a simple navigation experience similar to the reference
implementations in morebnyemba/hanna and morebnyemba/Kalai-Safaris, while
sticking to the step and condition types supported in this project.
"""

MAIN_MENU_FLOW = {
    "name": "main_menu",
    "friendly_name": "Main Menu",
    "description": "Top-level navigation for Sungrip Solar customers.",
    "trigger_keywords": ["menu", "start", "hello", "hi", "sungrip", "help"],
    "is_active": True,
    "steps": [
        {
            "name": "welcome",
            "type": "send_message",
            "is_entry_point": True,
            "config": {
                "message": "Welcome to Sungrip Solar!",
                "message_type": "text",
                "text": {
                    "body": (
                        "👋 Hi there! I'm the Sungrip assistant.\n"
                        "How can we help you today?"
                    )
                }
            },
            "transitions": [
                {
                    "to_step": "main_menu_prompt",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "main_menu_prompt",
            "type": "question",
            "config": {
                "question_text": "Choose an option",
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": (
                            "Please reply with a number:\n"
                            "1) View solar packages\n"
                            "2) Book a site assessment\n"
                            "3) Request a solar quote"
                        )
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "context_variable": "menu_choice"
                }
            },
            "transitions": [
                {
                    "to_step": "go_to_package_flow",
                    "priority": 1,
                    "condition_config": {
                        "type": "user_reply_matches",
                        "keywords": ["1", "package", "packages"],
                        "match_type": "contains"
                    }
                },
                {
                    "to_step": "go_to_assessment_flow",
                    "priority": 2,
                    "condition_config": {
                        "type": "user_reply_matches",
                        "keywords": ["2", "assessment", "visit", "site"],
                        "match_type": "contains"
                    }
                },
                {
                    "to_step": "go_to_quote_flow",
                    "priority": 3,
                    "condition_config": {
                        "type": "user_reply_matches",
                        "keywords": ["3", "quote", "pricing", "price"],
                        "match_type": "contains"
                    }
                },
                {
                    "to_step": "main_menu_retry",
                    "priority": 99,
                    "condition_config": {"type": "auto"}
                }
            ]
        },
        {
            "name": "go_to_package_flow",
            "type": "switch_flow",
            "config": {
                "target_flow": "package_viewing"
            },
            "transitions": []
        },
        {
            "name": "go_to_assessment_flow",
            "type": "switch_flow",
            "config": {
                "target_flow": "assessment_booking"
            },
            "transitions": []
        },
        {
            "name": "go_to_quote_flow",
            "type": "switch_flow",
            "config": {
                "target_flow": "solar_quote_request"
            },
            "transitions": []
        },
        {
            "name": "main_menu_retry",
            "type": "send_message",
            "config": {
                "message": "Let's try that again.",
                "message_type": "text",
                "text": {
                    "body": (
                        "Sorry, I didn't get that. Please reply with 1, 2, or 3."
                    )
                }
            },
            "transitions": [
                {
                    "to_step": "main_menu_prompt",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        }
    ]
}


PACKAGE_VIEWING_FLOW = {
    "name": "package_viewing",
    "friendly_name": "Package Viewing",
    "description": "Helps customers review popular solar packages and move to booking.",
    "trigger_keywords": ["packages", "package", "solar packages"],
    "is_active": True,
    "steps": [
        {
            "name": "package_intro",
            "type": "send_message",
            "is_entry_point": True,
            "config": {
                "message": "Review Sungrip packages",
                "message_type": "text",
                "text": {
                    "body": (
                        "I can share our popular solar packages.\n"
                        "Reply with a number to learn more:\n"
                        "1) Starter 3kW (apartments & small homes)\n"
                        "2) Family 5kW (typical family home)\n"
                        "3) Business 10kW (shops & small offices)"
                    )
                }
            },
            "transitions": [
                {
                    "to_step": "choose_package",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "choose_package",
            "type": "question",
            "config": {
                "question_text": "Which package would you like?",
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": (
                            "Choose a package (1, 2, or 3):\n"
                            "1) Starter 3kW\n"
                            "2) Family 5kW\n"
                            "3) Business 10kW"
                        )
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "context_variable": "package_choice"
                }
            },
            "transitions": [
                {
                    "to_step": "starter_details",
                    "priority": 1,
                    "condition_config": {
                        "type": "user_reply_matches",
                        "keywords": ["1", "starter", "3kw"],
                        "match_type": "contains"
                    }
                },
                {
                    "to_step": "family_details",
                    "priority": 2,
                    "condition_config": {
                        "type": "user_reply_matches",
                        "keywords": ["2", "family", "5kw"],
                        "match_type": "contains"
                    }
                },
                {
                    "to_step": "business_details",
                    "priority": 3,
                    "condition_config": {
                        "type": "user_reply_matches",
                        "keywords": ["3", "business", "10kw"],
                        "match_type": "contains"
                    }
                },
                {
                    "to_step": "packages_fallback",
                    "priority": 99,
                    "condition_config": {"type": "auto"}
                }
            ]
        },
        {
            "name": "starter_details",
            "type": "send_message",
            "config": {
                "message": "Starter package details",
                "message_type": "text",
                "text": {
                    "body": (
                        "🌞 *Starter 3kW*\n"
                        "- Perfect for apartments & small homes\n"
                        "- Powers lights, TV, Wi-Fi, and a fridge\n"
                        "- Typical price: ~$4,500 installed\n\n"
                        "Reply 'book' to schedule a site assessment, "
                        "'packages' to view options again, or 'menu' to return."
                    )
                }
            },
            "transitions": [
                {
                    "to_step": "package_next_steps",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "family_details",
            "type": "send_message",
            "config": {
                "message": "Family package details",
                "message_type": "text",
                "text": {
                    "body": (
                        "🏠 *Family 5kW*\n"
                        "- Ideal for most family homes\n"
                        "- Runs lighting, multiple TVs, internet, fridge, and small appliances\n"
                        "- Typical price: ~$7,200 installed\n\n"
                        "Reply 'book' to schedule a site assessment, "
                        "'packages' to view options again, or 'menu' to return."
                    )
                }
            },
            "transitions": [
                {
                    "to_step": "package_next_steps",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "business_details",
            "type": "send_message",
            "config": {
                "message": "Business package details",
                "message_type": "text",
                "text": {
                    "body": (
                        "🏢 *Business 10kW*\n"
                        "- Designed for shops and small offices\n"
                        "- Handles POS systems, networking, lighting, and refrigeration\n"
                        "- Typical price: ~$12,500 installed\n\n"
                        "Reply 'book' to schedule a site assessment, "
                        "'packages' to view options again, or 'menu' to return."
                    )
                }
            },
            "transitions": [
                {
                    "to_step": "package_next_steps",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "packages_fallback",
            "type": "send_message",
            "config": {
                "message": "Invalid package choice",
                "message_type": "text",
                "text": {
                    "body": "I didn't catch that. Please reply with 1, 2, or 3."
                }
            },
            "transitions": [
                {
                    "to_step": "choose_package",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "package_next_steps",
            "type": "question",
            "config": {
                "question_text": "Next action after package details",
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": (
                            "Would you like to book a free site assessment?\n"
                            "- Reply 'book' to schedule\n"
                            "- Reply 'packages' to view options again\n"
                            "- Reply 'menu' to return to the main menu"
                        )
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "context_variable": "package_next_action"
                }
            },
            "transitions": [
                {
                    "to_step": "switch_to_assessment_booking",
                    "priority": 1,
                    "condition_config": {
                        "type": "user_reply_matches",
                        "keywords": ["book", "yes", "assessment"],
                        "match_type": "contains"
                    }
                },
                {
                    "to_step": "choose_package",
                    "priority": 2,
                    "condition_config": {
                        "type": "user_reply_matches",
                        "keywords": ["packages", "back", "options"],
                        "match_type": "contains"
                    }
                },
                {
                    "to_step": "return_to_main_menu",
                    "priority": 3,
                    "condition_config": {
                        "type": "user_reply_matches",
                        "keywords": ["menu", "home"],
                        "match_type": "contains"
                    }
                },
                {
                    "to_step": "package_no_action",
                    "priority": 99,
                    "condition_config": {"type": "auto"}
                }
            ]
        },
        {
            "name": "switch_to_assessment_booking",
            "type": "switch_flow",
            "config": {
                "target_flow": "assessment_booking"
            },
            "transitions": []
        },
        {
            "name": "return_to_main_menu",
            "type": "switch_flow",
            "config": {
                "target_flow": "main_menu"
            },
            "transitions": []
        },
        {
            "name": "package_no_action",
            "type": "send_message",
            "config": {
                "message": "Package browsing ended",
                "message_type": "text",
                "text": {
                    "body": (
                        "No problem. If you need anything else, reply 'menu' to go back."
                    )
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


ASSESSMENT_BOOKING_FLOW = {
    "name": "assessment_booking",
    "friendly_name": "Assessment Booking",
    "description": "Collects details to book a site assessment with the Sungrip team.",
    "trigger_keywords": ["assessment", "site visit", "site assessment", "book visit"],
    "is_active": True,
    "steps": [
        {
            "name": "assessment_welcome",
            "type": "send_message",
            "is_entry_point": True,
            "config": {
                "message": "Book a site assessment",
                "message_type": "text",
                "text": {
                    "body": (
                        "Let's schedule a site assessment. I'll need a few details to confirm."
                    )
                }
            },
            "transitions": [
                {
                    "to_step": "ask_full_name",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_full_name",
            "type": "question",
            "config": {
                "question_text": "What is your full name?",
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "What is your full name?"}
                },
                "reply_config": {
                    "expected_type": "text",
                    "context_variable": "assessment_name"
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
                "question_text": "Where is the site located?",
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "Where is the site located? (city or address)"}
                },
                "reply_config": {
                    "expected_type": "text",
                    "context_variable": "assessment_location"
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
                "question_text": "Preferred date or day",
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "What date or day suits you for the visit? (e.g., 15 Feb or next Tuesday)"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "context_variable": "assessment_preferred_date"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_contact_number",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_contact_number",
            "type": "question",
            "config": {
                "question_text": "Best contact number",
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "What is the best contact number for the visit?"}
                },
                "reply_config": {
                    "expected_type": "text",
                    "context_variable": "assessment_contact_number"
                }
            },
            "transitions": [
                {
                    "to_step": "confirm_booking",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "confirm_booking",
            "type": "send_message",
            "config": {
                "message": "Assessment booking confirmation",
                "message_type": "text",
                "text": {
                    "body": (
                        "Great! We have your request:\n"
                        "• Name: {{assessment_name}}\n"
                        "• Location: {{assessment_location}}\n"
                        "• Preferred date: {{assessment_preferred_date}}\n"
                        "• Contact: {{assessment_contact_number}}\n\n"
                        "Our team will call to confirm the exact time. Anything else you want to add?"
                    )
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
