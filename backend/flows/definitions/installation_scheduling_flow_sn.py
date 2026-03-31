# backend/flows/definitions/installation_scheduling_flow_sn.py

"""
Installation scheduling conversational flow — Shona version.

Books solar system installation appointments for customers.
All user-facing text is in Shona.
"""

INSTALLATION_SCHEDULING_FLOW_SN = {
    "name": "installation_scheduling_sn",
    "friendly_name": "Installation Scheduling (Shona)",
    "description": "Kubhukura kuiswa kwemasolar neShona",
    "is_active": True,
    "trigger_keywords": ["schedule_sn", "isa_sn", "bhukura_sn"],
    "steps": [
        # ── Entry: ensure customer profile exists ──────────────────────
        {
            "name": "ensure_profile",
            "is_entry_point": True,
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "ensure_customer_profile",
                    "parameters": {}
                }]
            },
            "transitions": [
                {
                    "to_step": "check_whatsapp_flow",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── WhatsApp Flow integration check ────────────────────────────
        {
            "name": "check_whatsapp_flow",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "check_whatsapp_flow",
                    "parameters": {
                        "flow_name": "installation_scheduling_whatsapp",
                        "save_to_variable": "wa_flow_data"
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "send_whatsapp_flow",
                    "priority": 1,
                    "condition_config": {
                        "type": "variable_exists",
                        "variable_name": "wa_flow_data"
                    }
                },
                {
                    "to_step": "fallback_welcome",
                    "priority": 2,
                    "condition_config": {"type": "always_true"}
                }
            ]
        },
        # ── WhatsApp Flow path ─────────────────────────────────────────
        {
            "name": "send_whatsapp_flow",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "send_whatsapp_flow",
                    "parameters": {
                        "flow_variable": "wa_flow_data"
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "wait_for_whatsapp_response",
                    "priority": 1,
                    "condition_config": {"type": "always_true"}
                }
            ]
        },
        {
            "name": "wait_for_whatsapp_response",
            "type": "action",
            "config": {
                "actions_to_run": [],
                "wait_for": "whatsapp_flow_response"
            },
            "transitions": [
                {
                    "to_step": "map_wa_install_fields",
                    "priority": 1,
                    "condition_config": {"type": "whatsapp_flow_response_received"}
                }
            ]
        },
        # ── Map WA field names ─────────────────────────────────────────
        {
            "name": "map_wa_install_fields",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "map_wa_response",
                    "parameters": {
                        "mappings": {
                            "address": "installation_address",
                            "contact_name": "customer_name"
                        }
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "wa_ask_location_pin",
                    "priority": 1,
                    "condition_config": {
                        "type": "variable_exists",
                        "variable_name": "package_name"
                    }
                },
                {
                    "to_step": "build_packages_list",
                    "priority": 2,
                    "condition_config": {"type": "auto"}
                }
            ]
        },
        # ── WA path: ask missing fields ────────────────────────────
        {
            "name": "wa_ask_payment",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "💳 Nzira Yekubhadhara"},
                        "body": {
                            "text": "Mazvita nekuzadza fomu! Tine zvishoma zvatinodawo kuziva.\n\n"
                                    "Munoda kubhadhara sei?\n\n"
                                    "💵 *Mari Yese* — Bhadharai pakuiswa\n"
                                    "🔥 *Chirongwa che3 Mwedzi* — Chikafu chepfupi\n"
                                    "📆 *Chirongwa che6 Mwedzi* — Paradzai pamwedzi 6"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "cash", "title": "💵 Mari Yese"}},
                                {"type": "reply", "reply": {"id": "installment_3", "title": "🔥 3 Mwedzi"}},
                                {"type": "reply", "reply": {"id": "installment_6", "title": "📆 6 Mwedzi"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "package_payment_label"
                }
            },
            "transitions": [
                {
                    "to_step": "wa_ask_system",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "wa_ask_system",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {
                            "text": "⚡ Munoda system ipi ikiswe?"
                        },
                        "footer": {
                            "text": "Mitengo muUSD · Kuiswa kwakabatanidzwa"
                        },
                        "action": {
                            "button": "Sarudzai System",
                            "sections": [
                                {
                                    "title": "Masystem Aripo",
                                    "rows": [
                                        {"id": "3.5kva", "title": "⚡ 3.5 kVA System", "description": "Imba diki · Fridge, TV, magetsi"},
                                        {"id": "4.2kva", "title": "⚡ 4.2 kVA System", "description": "Imba yepakati · + Cameras, pombi"},
                                        {"id": "6.2kva", "title": "⚡ 6.2 kVA System", "description": "Imba huru · 3 fridges, 1.5HP pombi"},
                                        {"id": "not_sure", "title": "🤔 Handina Chokwadi", "description": "Tirimu yedu ichakurudzirai"}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "package_name"
                }
            },
            "transitions": [
                {
                    "to_step": "wa_ask_location_pin",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "wa_ask_location_pin",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📌 Tumirai *location pin* yenyu kuti tirimu yedu ikuwanei.\n\n"
                                "Dzvanyai 📎 → 📍 Location → Send"
                    }
                },
                "reply_config": {
                    "expected_type": "location",
                    "save_to_variable": "location_pin"
                }
            },
            "transitions": [
                {
                    "to_step": "format_install_labels",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Legacy conversational fallback ─────────────────────────────
        {
            "name": "fallback_welcome",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "📅 *Bukurai Kuiswa Kwemasolar Kwenyu*\n\n"
                            "Tinoisa masolar system ku*madzimba, mabhizinesi nemafarm* "
                            "muZimbabwe yese.\n\n"
                            "✅ Kubhadhara mushure mekuiswa (Supply & Fix)\n"
                            "✅ Nzira 3 dzekubhadhara: Mari yese, 3 mwedzi, ne6 mwedzi\n\n"
                            "Regai ndikuratidzei mapackage atiinawo kuti musarudze "
                            "yakakodzera — izvi zvinotora maminetsi mashoma chete ⏱️"
                }
            },
            "transitions": [
                {
                    "to_step": "build_packages_list",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Build dynamic packages list from DB ────────────────────────
        {
            "name": "build_packages_list",
            "type": "action",
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
                    "to_step": "capture_package_selection",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Capture package selection ──────────────────────────────────
        {
            "name": "capture_package_selection",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "👆 Dzvanyai *Onai Mapackage* pamusoro kuti muone, mosarudza package yamunoda kuiswa."
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
                    "to_step": "load_package_details",
                    "condition_config": {"type": "auto"},
                    "priority": 2
                }
            ]
        },
        # ── Load full package details ──────────────────────────────────
        {
            "name": "load_package_details",
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
                    "to_step": "show_package_and_proceed",
                    "condition_config": {
                        "type": "expression",
                        "expression": "package_found == True"
                    },
                    "priority": 1
                },
                {
                    "to_step": "build_packages_list",
                    "condition_config": {"type": "always_true"},
                    "priority": 2
                }
            ]
        },
        # ── Show package details + payment options ─────────────────────
        {
            "name": "show_package_and_proceed",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "{{package_detail_text}}\n\n"
                            "━━━━━━━━━━━━━━━━━━━━\n"
                            "💳 *Nzira 3 Dzekubhadhara:*\n"
                            "  1️⃣ *Mari Yese* — Bhadharai kamwe chete mocheneswa\n"
                            "  2️⃣ *Chirongwa che3 Mwedzi* — Paradzai pamwedzi 3\n"
                            "  3️⃣ *Chirongwa che6 Mwedzi* — Paradzai pamwedzi 6\n\n"
                            "✅ *Kubhadhara mushure mekuiswa*\n"
                            "   (Supply & Fix — tinoendeswa, toiswa, mobhadhara)\n"
                            "━━━━━━━━━━━━━━━━━━━━"
                }
            },
            "transitions": [
                {
                    "to_step": "wa_ask_location_pin",
                    "priority": 1,
                    "condition_config": {
                        "type": "variable_exists",
                        "variable_name": "whatsapp_flow_response_received"
                    }
                },
                {
                    "to_step": "ask_preferred_date",
                    "condition_config": {"type": "auto"},
                    "priority": 2
                }
            ]
        },
        # ── Date & time ────────────────────────────────────────────────
        {
            "name": "ask_preferred_date",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📅 Munoda kuisirwa rinhi?\n\n"
                                "_semuenzaniso: Monday, Vhiki rinouya, 15 March_"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "preferred_date"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_time_preference",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_time_preference",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "🕐 Nguva ipi yakanakisisa?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "morning", "title": "🌅 Mangwanani"}},
                                {"type": "reply", "reply": {"id": "afternoon", "title": "🌇 Masikati"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "time_preference"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_installation_address",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Address & location ─────────────────────────────────────────
        {
            "name": "ask_installation_address",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "🏠 Ndapota tipei *kero yakazara* yekuiswa:\n\n"
                                "_semuenzaniso: 42 Solar Drive, Borrowdale, Harare_\n\n"
                                "ℹ️ Kunze kweHarare — mari yekufambisa inogona kuvepo."
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "installation_address"
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
        {
            "name": "ask_location_pin",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📌 Tumirai *location pin* yenyu kuti tirimu yedu ikuwanei.\n\n"
                                "Dzvanyai 📎 → 📍 Location → Send"
                    }
                },
                "reply_config": {
                    "expected_type": "location",
                    "save_to_variable": "location_pin"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_additional_notes",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Optional notes ─────────────────────────────────────────────
        {
            "name": "ask_additional_notes",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "📝 Mune mamwe mashoko etirimu yekuisa here?\n\n"
                                    "_semuenzaniso: Gate access, rudzi rwedenga, zvinodiwa zvakasiyana_"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "no_notes", "title": "➡️ Tsvedzerai"}},
                                {"type": "reply", "reply": {"id": "add_notes", "title": "📝 Isai Mashoko"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "notes_choice"
                }
            },
            "transitions": [
                {
                    "to_step": "collect_notes",
                    "priority": 1,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "add_notes"
                    }
                },
                {
                    "to_step": "format_install_labels",
                    "priority": 2,
                    "condition_config": {"type": "always_true"}
                }
            ]
        },
        {
            "name": "collect_notes",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📝 Nyorai mashoko enyu pasi:"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "additional_notes"
                }
            },
            "transitions": [
                {
                    "to_step": "format_install_labels",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Format raw IDs to readable labels ──────────────────────
        {
            "name": "format_install_labels",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "format_labels",
                    "parameters": {
                        "variables": ["time_preference"]
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "confirm_installation",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Confirmation ───────────────────────────────────────────────
        {
            "name": "confirm_installation",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "📋 Tsinhiro Yebhukuro"},
                        "body": {
                            "text": "Mhoro {{customer_name}}, ongoroai bhukuro renyu:\n\n"
                                    "━━━━━━━━━━━━━━━━━━━━\n"
                                    "📦 *Package:* {{package_name}}\n"
                                    "💳 *Kubhadhara:* {{package_payment_label}}\n"
                                    "📅 *Zuva:* {{preferred_date}}\n"
                                    "🕐 *Nguva:* {{time_preference}}\n"
                                    "🏠 *Kero:* {{installation_address}}\n"
                                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                                    "Dzvanyai *Simbisai* kutumira kana *Shandurai* kutanga patsva."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_install", "title": "✅ Simbisai"}},
                                {"type": "reply", "reply": {"id": "edit_install", "title": "✏️ Shandurai"}},
                                {"type": "reply", "reply": {"id": "cancel_install", "title": "❌ Kanzirai"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "install_confirmation"
                }
            },
            "transitions": [
                {
                    "to_step": "save_and_notify_install",
                    "priority": 1,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "confirm_install"
                    }
                },
                {
                    "to_step": "fallback_welcome",
                    "priority": 2,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "edit_install"
                    }
                },
                {
                    "to_step": "end_cancelled",
                    "priority": 3,
                    "condition_config": {"type": "always_true"}
                }
            ]
        },
        # ── Save to DB & notify team ──────────────────────────────────
        {
            "name": "save_and_notify_install",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "save_installation_request",
                        "parameters": {}
                    },
                    {
                        "action_type": "send_group_notification",
                        "parameters": {
                            "template_name": "sungrip_new_installation_request",
                            "group_names": ["Sales Team"]
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "confirm_scheduling",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Success ────────────────────────────────────────────────────
        {
            "name": "confirm_scheduling",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "✅ *Kuiswa Kwabhukurwa!*\n\n"
                            "Mazvita, {{customer_name}}! Hei bhukuro renyu:\n\n"
                            "📦 Package: {{package_name}}\n"
                            "💳 Kubhadhara: {{package_payment_label}}\n"
                            "📅 Zuva: {{preferred_date}}\n"
                            "🕐 Nguva: {{time_preference}}\n"
                            "🏠 Kero: {{installation_address}}\n\n"
                            "Tirimu yedu yekuisa ichakufonai mukati me*maawa 24* "
                            "kuti tisimbise zuva chairo.\n\n"
                            "📞 WhatsApp: 0782 233 111 / 0777 139 159\n\n"
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
        # ── Route to quote flow ────────────────────────────────────
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
        {
            "name": "end_cancelled",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "❌ *Bhukuro radzimwa.*\n\n"
                            "Hapana dambudziko! Munogona kubhukura patsva nguva dzese nokunyora *schedule*.\n"
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
