# backend/flows/definitions/contact_support_flow_sn.py

"""
Contact-support conversational flow — Shona version.

Connects customers with the Sungrip support team.  Collects issue
category, description, and preferred contact method, then confirms
that a support ticket has been raised.  All user-facing text in Shona.
"""

CONTACT_SUPPORT_FLOW_SN = {
    "name": "contact_support_sn",
    "friendly_name": "Contact Support (Shona)",
    "description": "Kubatanidza vashandisi netirimu yerubatsiro neShona",
    "is_active": True,
    "trigger_keywords": ["rubatsiro", "batsira", "dambudziko", "ndibatsirei"],
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
                        "flow_name": "contact_support_whatsapp",
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
                    "to_step": "map_wa_support_fields",
                    "priority": 1,
                    "condition_config": {"type": "whatsapp_flow_response_received"}
                }
            ]
        },
        # ── Map WA field names ─────────────────────────────────────────
        {
            "name": "map_wa_support_fields",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "map_wa_response",
                    "parameters": {
                        "mappings": {
                            "issue_description": "issue_details",
                            "contact_preference": "contact_method"
                        }
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "format_support_labels",
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
                    "body": "💬 *Rubatsiro rweVashandisi veSungrip*\n\n"
                            "Tiri pano kukubatsirai! Regai ndikwanise mashoko mashoma "
                            "kuti tirimu yedu ikubatsirei nekukurumidza."
                }
            },
            "transitions": [
                {
                    "to_step": "ask_support_category",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_support_category",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {
                            "text": "📋 Munodei rubatsiro pachipi?\n\n"
                                    "Sarudzai chikamu chakakodzera kubvunzo yenyu."
                        },
                        "footer": {
                            "text": "Sungrip Rubatsiro"
                        },
                        "action": {
                            "button": "Sarudzai Chikamu",
                            "sections": [
                                {
                                    "title": "Zvikamu zveRubatsiro",
                                    "rows": [
                                        {
                                            "id": "technical",
                                            "title": "🔧 Matambudziko eTechnical",
                                            "description": "System faults, inverter errors, panel issue"
                                        },
                                        {
                                            "id": "billing",
                                            "title": "💳 Mabhiri neKubhadhara",
                                            "description": "Ma-invoice, machirongwa ekubhadhara, refunds"
                                        },
                                        {
                                            "id": "installation",
                                            "title": "🏗️ Rubatsiro rweKuiswa",
                                            "description": "Mazuva ekuiswa, kuona nzvimbo"
                                        },
                                        {
                                            "id": "product_info",
                                            "title": "📦 Ruzivo rweZviwanikwa",
                                            "description": "Specs, warranties, kushanda pamwe"
                                        },
                                        {
                                            "id": "other",
                                            "title": "📝 Zvimwe",
                                            "description": "Chimwe chese chatinokubatsirai nacho"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "support_category"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_issue_details",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_issue_details",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "📝 Ndapota *tsanangurai dambudziko kana mubvunzo wenyu* nemashoko mashoma.\n\n"
                                "Zvakawanda zvamunotaura, tinokurumidza kukubatsirai!"
                    }
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "issue_details"
                }
            },
            "transitions": [
                {
                    "to_step": "ask_contact_method",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "ask_contact_method",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "📞 Tirimu yedu yerubatsiro inofanira kukubatai sei?\n\n"
                                    "Sarudzai nzira yamunoda."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "whatsapp", "title": "💬 WhatsApp"}},
                                {"type": "reply", "reply": {"id": "phone_call", "title": "📞 Foni"}},
                                {"type": "reply", "reply": {"id": "email", "title": "📧 Email"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "contact_method"
                }
            },
            "transitions": [
                {
                    "to_step": "format_support_labels",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Format raw IDs to readable labels ──────────────────────
        {
            "name": "format_support_labels",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "format_labels",
                    "parameters": {
                        "variables": ["support_category", "contact_method"]
                    }
                }]
            },
            "transitions": [
                {
                    "to_step": "confirm_support_request",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Confirmation with interactive buttons ──────────────────────
        {
            "name": "confirm_support_request",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "💬 Ongoroai Rubatsiro Rwenyu"},
                        "body": {
                            "text": "Mhoro {{customer_name}}, simbisai kukumbira rubatsiro kwenyu:\n\n"
                                    "━━━━━━━━━━━━━━━━━━━━\n"
                                    "📋 *Chikamu:* {{support_category}}\n"
                                    "📝 *Tsananguro:* {{issue_details}}\n"
                                    "📞 *Kubatana ne:* {{contact_method}}\n"
                                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                                    "Dzvanyai *Tumirai* kutumira kana *Shandurai* kutanga patsva."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_support", "title": "✅ Tumirai"}},
                                {"type": "reply", "reply": {"id": "edit_support", "title": "✏️ Shandurai"}},
                                {"type": "reply", "reply": {"id": "cancel_support", "title": "❌ Kanzirai"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "support_confirmation"
                }
            },
            "transitions": [
                {
                    "to_step": "save_and_notify_support",
                    "priority": 1,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "confirm_support"
                    }
                },
                {
                    "to_step": "fallback_welcome",
                    "priority": 2,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "edit_support"
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
            "name": "save_and_notify_support",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "save_support_request",
                        "parameters": {}
                    },
                    {
                        "action_type": "send_group_notification",
                        "parameters": {
                            "template_name": "sungrip_new_support_request",
                            "group_names": ["Support Team", "Sales Team"]
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "confirm_support",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # ── Success & closing ──────────────────────────────────────────
        {
            "name": "confirm_support",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "✅ *Kukumbira rubatsiro kwatumirwa!*\n\n"
                            "Mazvita, {{customer_name}}! Hei tsinhiro:\n\n"
                            "📋 Chikamu: {{support_category}}\n"
                            "📞 Tichakubatai ne: {{contact_method}}\n\n"
                            "Tirimu yedu yerubatsiro ichadzoka mukati me*maawa 24*. "
                            "Kana mune urgency, WhatsApp *0782 233 111 / 0777 139 159*.\n\n"
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
                    "body": "❌ *Kukumbira rubatsiro kwadzimwa.*\n\n"
                            "Hapana dambudziko! Munogona kutibata nguva dzese nokunyora *rubatsiro*.\n"
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
