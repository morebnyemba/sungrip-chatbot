# backend/flows/definitions/solar_packages_flow.py

"""
Solar packages flow definition.

Displays available solar system packages in a WhatsApp interactive list,
shows full details on selection, and offers booking or browsing another.

Package data is loaded dynamically from the SolarPackage model via
registered actions so that pricing, features, and availability are always
up to date and admin-configurable.
"""

SOLAR_PACKAGES_FLOW = {
    "name": "solar_packages",
    "friendly_name": "Solar Packages",
    "description": "Browse solar packages interactively (DB-driven dynamic list)",
    "is_active": True,
    "trigger_keywords": ["packages", "systems", "options", "what do you have", "pricing"],
    "steps": [
        # ── Step 1: Build interactive list from DB ──────────────────────
        {
            "name": "build_list",
            "type": "action",
            "is_entry_point": True,
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "build_packages_interactive_list",
                        "parameters": {}
                    },
                    {
                        "action_type": "send_dynamic_message",
                        "parameters": {
                            "message_variable": "_packages_list_msg"
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "capture_selection",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Step 2: Wait for user to tap a package ─────────────────────
        {
            "name": "capture_selection",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "👆 Tap *View Packages* above to browse, then select a package to see full details."
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "selected_package"
                }
            },
            "transitions": [
                {
                    "to_step": "load_details",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Step 3: Look up full package details ───────────────────────
        {
            "name": "load_details",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "fetch_package_details",
                        "parameters": {
                            "selection_variable": "selected_package"
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "show_details",
                    "condition_config": {
                        "type": "expression",
                        "expression": "package_found == True"
                    },
                    "priority": 1
                },
                {
                    "to_step": "build_list",
                    "condition_config": {"type": "always_true"},
                    "priority": 2
                }
            ]
        },
        # ── Step 4: Display full details + warranty info ───────────────
        {
            "name": "show_details",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "{{package_detail_text}}\n\n"
                           "━━━━━━━━━━━━━━━━━━━━\n"
                           "🛡️ *Warranty & Support:*\n"
                           "  • 25-Year Panel Warranty\n"
                           "  • 5-Year Inverter Warranty\n"
                           "  • Lifetime Technical Support\n"
                           "  • Payment after delivery & installation\n"
                           "━━━━━━━━━━━━━━━━━━━━"
                }
            },
            "transitions": [
                {
                    "to_step": "next_action",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Step 5: What would you like to do next? ────────────────────
        {
            "name": "next_action",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "What would you like to do next?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "book_install", "title": "📅 Book Install"}},
                                {"type": "reply", "reply": {"id": "view_another", "title": "🔄 View Another"}},
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
                    "to_step": "switch_to_install",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "book_install"
                    },
                    "priority": 1
                },
                {
                    "to_step": "build_list",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "view_another"
                    },
                    "priority": 2
                },
                {
                    "to_step": "thank_you",
                    "condition_config": {"type": "always_true"},
                    "priority": 3
                }
            ]
        },
        # ── Route to installation booking flow ─────────────────────────
        {
            "name": "switch_to_install",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "installation_scheduling",
                "message": "Great choice! Let's book your *{{package_name}}* installation. 📅",
                "initial_context_template": {
                    "package_interest": "{{package_name}}"
                }
            },
            "transitions": []
        },
        # ── Thank you & end ────────────────────────────────────────────
        {
            "name": "thank_you",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Thank you for exploring our solar packages! 🌞\n\n"
                           "If you have any questions, feel free to message us anytime.\n"
                           "Type *menu* to return to the main menu."
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
