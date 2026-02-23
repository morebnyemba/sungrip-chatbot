# backend/flows/definitions/order_delivery_info_flow_sn.py

"""
Order delivery information collection flow — Shona version.

Triggered programmatically after a WhatsApp Commerce Catalog order is
created.  Collects recipient name, phone number, delivery address, and
an optional location pin, then persists the details and sends
confirmation + team notifications.  All user-facing text in Shona.
"""

ORDER_DELIVERY_INFO_FLOW_SN = {
    "name": "order_delivery_info_sn",
    "friendly_name": "Order Delivery Info (Shona)",
    "description": (
        "Inounganidza ruzivo rwekuendeswa (munogamuchira, kero, nzvimbo) "
        "mushure mekuisa order neWhatsApp Commerce neShona."
    ),
    "is_active": True,
    # Never triggered by keywords — only started programmatically
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
                            "🎉 *Order {{order_number}} yagamuchirwa — mazvita!*\n\n"
                            "Kuti tipedze order yenyu tinoda ruzivo rwekuendeswa rushoma.\n\n"
                            "👤 Ndiani *zita rakazara* remunhu anogamuchira "
                            "chiendeswa ichi?"
                        )
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "recipient_name"
                },
                "fallback_config": {
                    "re_prompt_message_text": (
                        "⚠️ Ndapota nyorai *zita rakazara* remunhu anogamuchira."
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
                            "📱 Ndeupi *nhamba yefoni* yemunhu anogamuchira?\n\n"
                            "Isanganisirai country code, semuenzaniso +263 7XX XXX XXX"
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
                        "⚠️ Nhamba iyoyo haiiti seyerunhare.\n"
                        "Ndapota isai nhamba yakafanana ne +263 7XX XXX XXX."
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
                            "🏠 Ndeipi *kero yekuendeswa*?\n\n"
                            "Ndapota isanganisirai nzvimbo, mugwagwa, nedhorobha."
                        )
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "delivery_address"
                },
                "fallback_config": {
                    "re_prompt_message_text": (
                        "⚠️ Ndapota nyorai kero yakazara yekuendeswa "
                        "(mugwagwa, nzvimbo, dhorobha)."
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
                                "📍 Munoda kutumira *location pin* yenyu "
                                "kuti kuendeswa kuve nyore here?\n\n"
                                "Dzvanyai 📎 → 📍 Location kutumira pin yenyu, "
                                "kana dzvanyai *Tsvedzerai* kuti muenderere pasina."
                            )
                        },
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {
                                        "id": "skip_location",
                                        "title": "Tsvedzerai"
                                    }
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "location_pin"
                },
                "fallback_config": {
                    "re_prompt_message_text": (
                        "📍 Ndapota tumirai location pin yenyu, kana dzvanyai *Tsvedzerai* "
                        "kuti muenderere pasina."
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
