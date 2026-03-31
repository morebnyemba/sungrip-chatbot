# backend/flows/definitions/solar_packages_flow_sn.py

"""
Solar packages flow definition — Shona version.

Displays available solar system packages in a WhatsApp interactive list,
shows full details on selection, and offers booking or browsing another.
All user-facing text is in Shona.
"""

SOLAR_PACKAGES_FLOW_SN = {
    "name": "solar_packages_sn",
    "friendly_name": "Solar Packages (Shona)",
    "description": "Onai mapackage emasolar neShona (DB-driven dynamic list)",
    "is_active": True,
    "trigger_keywords": ["mapackage", "masystem", "mitengo", "munemei"],
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
                        "body": "👆 Dzvanyai *Onai Mapackage* pamusoro kuti muone, mosarudza package kuti muone zvakawanda."
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "selected_package"
                }
            },
            "transitions": [
                {
                    "to_step": "route_to_quote",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "get_quote"
                    },
                    "priority": 1
                },
                {
                    "to_step": "load_details",
                    "condition_config": {"type": "auto"},
                    "priority": 2
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
                            "💰 *Nzira 3 Dzekubhadhara:*\n"
                            "  1️⃣ *Mari Yese* — Bhadharai kamwe chete mocheneswa\n"
                            "  2️⃣ *Chirongwa che3 Mwedzi* — Paradzai pamwedzi 3\n"
                            "  3️⃣ *Chirongwa che6 Mwedzi* — Paradzai pamwedzi 6\n\n"
                            "✅ *Kubhadhara mushure mekuiswa*\n"
                            "   (Supply & Fix — tinoendeswa, toiswa, mobhadhara)\n\n"
                            "🛡️ *Warranty neRubatsiro:*\n"
                            "  • Warranty yeMakore 25 yeMaPanels\n"
                            "  • Warranty yeMakore 5 yeInverter\n"
                            "  • Rubatsiro rweGore Mushure Mekuiswa\n"
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
                        "type": "list",
                        "body": {
                            "text": "Munoda kuitei ikozvino?"
                        },
                        "action": {
                            "button": "Sarudzai",
                            "sections": [
                                {
                                    "title": "Zvamungaita",
                                    "rows": [
                                        {"id": "book_install", "title": "📅 Bukurai Kuiswa", "description": "Rongai zuva rekuiswa kwepackage iyi"},
                                        {"id": "get_custom_quote", "title": "📋 Wanai Quote", "description": "Munoda system yakasiyana? Tichakuitirai"},
                                        {"id": "view_another", "title": "🔄 Onai Imwe Package", "description": "Onai mamwe mapackage emasolar"},
                                        {"id": "back_menu", "title": "🏠 Main Menu", "description": "Dzokerai kumenyu huru"}
                                    ]
                                }
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
                    "to_step": "confirm_book_install",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "book_install"
                    },
                    "priority": 1
                },
                {
                    "to_step": "route_to_quote",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "get_custom_quote"
                    },
                    "priority": 2
                },
                {
                    "to_step": "build_list",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "view_another"
                    },
                    "priority": 3
                },
                {
                    "to_step": "thank_you",
                    "condition_config": {"type": "always_true"},
                    "priority": 4
                }
            ]
        },
        # ── Route to installation booking flow ─────────────────────────
        {
            "name": "confirm_book_install",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "📋 Simbisai Kubukura"},
                        "body": {
                            "text": "Mava kuda kubukura kuiswa kwe:\n\n"
                                    "━━━━━━━━━━━━━━━━━━━━\n"
                                    "📦 *Package:* {{package_name}}\n"
                                    "💰 *Mutengo:* {{package_price}}\n"
                                    "⚡ *System:* {{package_system_size}}\n"
                                    "💳 *Kubhadhara:* {{package_payment_label}}\n"
                                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                                    "Munoda kuenderera mberi here?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "yes_book", "title": "✅ Hongu, Bukurai"}},
                                {"type": "reply", "reply": {"id": "no_back", "title": "🔙 Dzokerai"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "book_confirmation"
                }
            },
            "transitions": [
                {
                    "to_step": "switch_to_install",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "yes_book"
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
        {
            "name": "switch_to_install",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "installation_scheduling_sn",
                "message": "Sarudzo yakanaka! Ngatibukurei kuiswa kwe *{{package_name}}*. 📅",
                "initial_context_template": {
                    "package_interest": "{{package_name}}",
                    "package_name": "{{package_name}}",
                    "package_price": "{{package_price}}",
                    "package_system_size": "{{package_system_size}}",
                    "package_payment_label": "{{package_payment_label}}",
                    "system_size": "{{system_size}}",
                    "payment_preference": "{{payment_preference}}"
                }
            },
            "transitions": []
        },
        # ── Route to quote flow for customised systems ────────────────
        {
            "name": "route_to_quote",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "solar_quote_request_sn",
                "message": "Hapana dambudziko! Ngatigadzire quote yenyu yemasolar. 📋",
                "initial_context_template": {}
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
                    "body": "Mazvita nekuona mapackage edu emasolar! 🌞\n\n"
                            "Kana muine mibvunzo, nyorai nguva dzese.\n"
                            "Nyorai *menyu* kuti mudzokere kumenyu huru."
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
