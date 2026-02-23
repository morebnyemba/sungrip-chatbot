# backend/flows/definitions/language_selection_flow.py

"""
Language selection flow definition.

Presented to first-time contacts before the main menu.
Lets the user choose between English and Shona, persists the
preference on the Contact record, then switches to the appropriate
main_menu variant.
"""

LANGUAGE_SELECTION_FLOW = {
    "name": "language_selection",
    "friendly_name": "Language Selection",
    "description": "Asks new users to choose their preferred language, then routes to the main menu",
    "is_active": True,
    # Not keyword-triggered — auto-started for first-time contacts
    "trigger_keywords": ["language", "mutauro", "chirungu", "shona"],
    "steps": [
        # ── Step 1: Ensure customer profile ────────────────────────
        {
            "name": "ensure_profile",
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
                    "to_step": "ask_language",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Step 2: Ask language preference ────────────────────────
        {
            "name": "ask_language",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {
                            "type": "text",
                            "text": "🌍 Language / Mutauro"
                        },
                        "body": {
                            "text": "Welcome to *Sungrip Solar*! 🌞\n"
                                    "Mauya ku *Sungrip Solar*! 🌞\n\n"
                                    "Please choose your preferred language:\n"
                                    "Sarudzai mutauro wamunoda:\n"
                        },
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {
                                        "id": "lang_en",
                                        "title": "🇬🇧 English"
                                    }
                                },
                                {
                                    "type": "reply",
                                    "reply": {
                                        "id": "lang_sn",
                                        "title": "🇿🇼 Shona"
                                    }
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "language_choice"
                }
            },
            "transitions": [
                {
                    "to_step": "save_shona",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "lang_sn"
                    },
                    "priority": 1
                },
                {
                    "to_step": "save_english",
                    "condition_config": {"type": "always_true"},
                    "priority": 2
                }
            ]
        },
        # ── Save English preference ────────────────────────────────
        {
            "name": "save_english",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "save_language_preference",
                        "parameters": {"language": "en"}
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "go_to_menu_en",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Save Shona preference ──────────────────────────────────
        {
            "name": "save_shona",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "save_language_preference",
                        "parameters": {"language": "sn"}
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "go_to_menu_sn",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Route to English main menu ─────────────────────────────
        {
            "name": "go_to_menu_en",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "main_menu",
                "message": "Great! Let's get started. 🌞",
                "initial_context_template": {}
            },
            "transitions": []
        },
        # ── Route to Shona main menu ───────────────────────────────
        {
            "name": "go_to_menu_sn",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "main_menu_sn",
                "message": "Zvakanakai! Ngatitangei. 🌞",
                "initial_context_template": {}
            },
            "transitions": []
        }
    ]
}
