# backend/flows/definitions/solar_quote_flow_sn.py

"""
Solar quote request conversational flow — Shona version.

Guides customers through requesting a solar system quote.
All user-facing text is in Shona.
"""

SOLAR_QUOTE_FLOW_SN = {
    "name": "solar_quote_request_sn",
    "friendly_name": "Solar Quote Request (Shona)",
    "description": "Inotungamirira vashandisi neShona pakukumbira quote yemasolar",
    "is_active": True,
    "trigger_keywords": ["quote_sn", "mutengo_sn"],
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
                        "flow_name": "solar_quote_whatsapp",
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
                    "to_step": "map_wa_quote_fields",
                    "priority": 1,
                    "condition_config": {"type": "whatsapp_flow_response_received"}
                }
            ]
        },
        # ── Map WA field names → conversational field names ──────────
        {
            "name": "map_wa_quote_fields",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "map_wa_response",
                    "parameters": {
                        "mappings": {}
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "wa_ask_property_type",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── WA path: ask missing fields ──────────────────────────────
        {
            "name": "wa_ask_property_type",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "Mazvita nekuzadza fomu! Tine zvishoma zvatinodawo kuziva.\n\n"
                                    "🏠 Imba yenyu ndeyerudzi rupi?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "residential", "title": "🏠 Yekugara"}},
                                {"type": "reply", "reply": {"id": "commercial", "title": "🏢 Yebhizinesi"}},
                                {"type": "reply", "reply": {"id": "industrial", "title": "🏭 Yefekitari"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "property_type"
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
        # ── WA path: ask missing location pin ────────────────────────
        {
            "name": "wa_ask_location_pin",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Mazvita nekuzadza fomu! Chimwe chekupedzisira:\n\n"
                                "📌 Tumirai *location pin* yenyu kuti tikwanise kuongorora nzvimbo yenyu.\n\n"
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
                    "to_step": "format_quote_labels",
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
                    "body": "📋 *Kukumbira Quote Yemasolar*\n\n"
                            "Sarudzo yakanaka! Ndichakubvunzai mibvunzo mishoma "
                            "kuti tigadzire quote yenyu yemasolar.\n\n"
                            "Izvi zvinotora maminetsi mashoma chete ⏱️"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_gadgets",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_gadgets",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "🔌 *Wanai Quote*\n\n"
                                "Ndedzipi nzira dzemagetsi nemachines amunoda kushandisa "
                                "nesolar kuti tikurudzirei system yakakodzera?\n\n"
                                "Nyorai gadgets dzenyu, semuenzaniso:\n"
                                "_TV, fridge, magetsi (6), laptop, microwave, pombi yemvura_\n\n"
                                "💡 *Zano:* Isai zvese zvamunoda kushandisa — zvakawanda zvamunotaura, "
                                "quote yenyu inova yakanyatsonaka!"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "gadgets_to_power"
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
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {
                            "text": "🏠 Denga renyu rakaitwa nei?\n\n"
                                    "Izvi zvinotibatsira kuziva nzira yakanakisisa yekuisa mapanels."
                        },
                        "footer": {
                            "text": "Sarudzai rudzi rwedenga renyu"
                        },
                        "action": {
                            "button": "Sarudzai Rudzi rweDenga",
                            "sections": [
                                {
                                    "title": "Marudzi eDenga",
                                    "rows": [
                                        {"id": "tile", "title": "Tile Roof", "description": "Matiles eclay kana concrete"},
                                        {"id": "metal", "title": "Metal / IBR", "description": "Marata esimbi"},
                                        {"id": "asbestos", "title": "Asbestos", "description": "Marata easbestos cement"},
                                        {"id": "concrete", "title": "Flat Concrete", "description": "Denga rakati sandara reconcrete"},
                                        {"id": "other", "title": "Zvimwe", "description": "Uswa, shingle, kana zvimwe"}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "roof_type"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_property_type",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_property_type",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "🏘️ Imba yenyu ndeyerudzi rupi?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "residential", "title": "🏠 Yekugara"}},
                                {"type": "reply", "reply": {"id": "commercial", "title": "🏢 Yebhizinesi"}},
                                {"type": "reply", "reply": {"id": "industrial", "title": "🏭 Yefekitari"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "property_type"
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
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📍 Muri muguta kana taundi ripi?\n\n"
                                "_semuenzaniso: Harare, Bulawayo, Mutare_"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "location"
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
                        "body": "📌 Tumirai *location pin* yenyu muchishandisa WhatsApp.\n\n"
                                "Dzvanyai 📎 (attach) → 📍 Location → Send.\n\n"
                                "Izvi zvinobatsira tirimu yedu kurongera kuongorora nzvimbo."
                    }
                },
                "reply_config": {
                    "expected_type": "location",
                    "save_to_variable": "location_pin"
                }
            },
            "transitions": [
                {
                    "to_step": "format_quote_labels",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Format raw IDs to readable labels ──────────────────────
        {
            "name": "format_quote_labels",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "format_labels",
                    "parameters": {
                        "variables": ["roof_type", "property_type"]
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "confirm_quote_request",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Confirmation with interactive buttons ──────────────────────
        {
            "name": "confirm_quote_request",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "📋 Ongoroai Quote Yenyu"},
                        "body": {
                            "text": "Mhoro {{customer_name}}, simbisai kukumbira quote kwenyu:\n\n"
                                    "━━━━━━━━━━━━━━━━━━━━\n"
                                    "🔌 *Zvinhu Zvinoda Magetsi:* {{gadgets_to_power}}\n"
                                    "🏠 *Rudzi rweDenga:* {{roof_type}}\n"
                                    "🏘️ *Rudzi rweImba:* {{property_type}}\n"
                                    "📍 *Nzvimbo:* {{location}}\n"
                                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                                    "Dzvanyai *Simbisai* kutumira kana *Shandurai* kutanga patsva."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_quote", "title": "✅ Simbisai"}},
                                {"type": "reply", "reply": {"id": "edit_quote", "title": "✏️ Shandurai"}},
                                {"type": "reply", "reply": {"id": "cancel_quote", "title": "❌ Kanzirai"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "quote_confirmation"
                }
            },
            "transitions": [
                {
                    "to_step": "save_and_notify_quote",
                    "priority": 1,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "confirm_quote"
                    }
                },
                {
                    "to_step": "fallback_welcome",
                    "priority": 2,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "edit_quote"
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
            "name": "save_and_notify_quote",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "save_quote_request",
                        "parameters": {}
                    },
                    {
                        "action_type": "send_group_notification",
                        "parameters": {
                            "template_name": "sungrip_new_quote_request",
                            "group_names": ["Sales Team"]
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "provide_quote",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Success & closing ──────────────────────────────────────────
        {
            "name": "provide_quote",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "✅ *Kukumbira quote kwatumirwa!*\n\n"
                            "Mazvita, {{customer_name}}! Hei tsinhiro:\n\n"
                            "🔌 Zvinhu: {{gadgets_to_power}}\n"
                            "🏠 Denga: {{roof_type}}\n"
                            "📍 Nzvimbo: {{location}}\n\n"
                            "Mumwe wemasolar consultant edu achaongorora zvamunodiwa "
                            "achakubatai mukati me*maawa 24* nequote yakagadzirirwa imi.\n\n"
                            "📞 Munoda nokukurumidza? WhatsApp *0782 233 111 / 0777 139 159*\n\n"
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
            "name": "end_cancelled",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "❌ *Kukumbira quote kwadzimwa.*\n\n"
                            "Hapana dambudziko! Munogona kutanga patsva nguva dzese nokunyora *quote*.\n"
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
