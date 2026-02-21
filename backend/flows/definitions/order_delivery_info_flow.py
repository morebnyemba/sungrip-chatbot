# backend/flows/definitions/order_delivery_info_flow.py

"""
Order delivery information collection flow.

Triggered programmatically after a WhatsApp Commerce Catalog order is
created.  Collects recipient name, phone number, delivery address, and
an optional location pin, then persists the details and sends
confirmation + team notifications.
"""

ORDER_DELIVERY_INFO_FLOW = {
    "name": "order_delivery_info",
    "friendly_name": "Order Delivery Info",
    "description": (
        "Collects delivery details (recipient, address, location) "
        "after a catalog order is placed via WhatsApp Commerce."
    ),
    "is_active": True,
    # Never triggered by keywords — only started programmatically
    # after process_order_from_catalog creates the Order.
    "trigger_keywords": [],
    "steps": [
        # ── Step 1: Ask recipient name ────────────────────────────
        {
            "name": "ask_recipient_name",
            "type": "question",
            "is_entry_point": True,
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": (
                            "🎉 *Order {{order_number}} received — thank you!*\n\n"
                            "To complete your order we need a few delivery details.\n\n"
                            "👤 What is the *full name* of the person receiving "
                            "this delivery?"
                        )
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "recipient_name"
                },
                "fallback_config": {
                    "re_prompt_message_text": (
                        "⚠️ Please type the *full name* of the recipient."
                    ),
                    "max_retries": 3,
                    "action_after_retries": "end_flow"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_recipient_phone",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Step 2: Ask recipient phone number ────────────────────
        {
            "name": "ask_recipient_phone",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": (
                            "📱 What is the *phone number* for the recipient?\n\n"
                            "Include the country code, e.g. +263 7XX XXX XXX"
                        )
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "recipient_phone",
                    "validation_regex": "^[\\+]?[0-9\\s\\-]{7,15}$"
                },
                "fallback_config": {
                    "re_prompt_message_text": (
                        "⚠️ That doesn't look like a valid phone number.\n"
                        "Please enter a number like +263 7XX XXX XXX."
                    ),
                    "max_retries": 3,
                    "action_after_retries": "end_flow"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_delivery_address",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Step 3: Ask delivery address ──────────────────────────
        {
            "name": "ask_delivery_address",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": (
                            "🏠 What is the *delivery address*?\n\n"
                            "Please include the street, area/suburb and city."
                        )
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "delivery_address"
                },
                "fallback_config": {
                    "re_prompt_message_text": (
                        "⚠️ Please type the full delivery address "
                        "(street, area, city)."
                    ),
                    "max_retries": 3,
                    "action_after_retries": "end_flow"
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
        # ── Step 4: Ask location pin (skippable) ─────────────────
        #
        # The user can either:
        #   • Send a WhatsApp location pin  (msg type = location)
        #   • Tap the "Skip" button
        #
        # Both are accepted by the question step because
        # _process_question_reply handles location and interactive
        # replies regardless of expected_type.
        {
            "name": "ask_location_pin",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": (
                                "📍 Would you like to share your *location pin* "
                                "for easier delivery?\n\n"
                                "Tap 📎 → 📍 Location to send your pin, "
                                "or tap *Skip* to continue without it."
                            )
                        },
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {
                                        "id": "skip_location",
                                        "title": "Skip"
                                    }
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    # text expected_type is the most permissive — it lets
                    # interactive (button) and location replies through as
                    # well via the fallback branches in _process_question_reply.
                    "expected_type": "text",
                    "save_to_variable": "location_pin"
                },
                "fallback_config": {
                    "re_prompt_message_text": (
                        "📍 Please send your location pin, or tap *Skip* "
                        "to continue without it."
                    ),
                    "max_retries": 2,
                    "action_after_retries": "end_flow"
                }
            },
            "transitions": [
                {
                    "to_step": "save_and_confirm",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "skip_location"
                    },
                    "priority": 1
                },
                {
                    "to_step": "save_and_confirm",
                    "condition_config": {"type": "auto"},
                    "priority": 2
                }
            ]
        },
        # ── Step 5: Save delivery info + send confirmation ────────
        {
            "name": "save_and_confirm",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "save_delivery_info",
                        "parameters": {}
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "end_order_flow",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Step 6: End flow ──────────────────────────────────────
        {
            "name": "end_order_flow",
            "type": "end_flow",
            "config": {},
            "transitions": []
        }
    ]
}
