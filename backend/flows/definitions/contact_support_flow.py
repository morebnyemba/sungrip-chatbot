# backend/flows/definitions/contact_support_flow.py

"""
Contact‑support conversational flow.

Connects customers with the Sungrip support team.  Collects issue
category, description, and preferred contact method, then confirms
that a support ticket has been raised.
"""

CONTACT_SUPPORT_FLOW = {
    "name": "contact_support",
    "friendly_name": "Contact Support",
    "description": "Connects customers with the Sungrip support team",
    "is_active": True,
    "trigger_keywords": ["support", "help", "contact", "problem", "issue"],
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
        # ── Map WA field names → conversational field names ──────────
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
                    "body": "💬 *Sungrip Customer Support*\n\n"
                           "We're here to help! Let me gather a few details "
                           "so our team can assist you as quickly as possible."
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
                            "text": "📋 What do you need help with?\n\n"
                                   "Select the category that best matches your enquiry."
                        },
                        "footer": {
                            "text": "Sungrip Support"
                        },
                        "action": {
                            "button": "Select Category",
                            "sections": [
                                {
                                    "title": "Support Categories",
                                    "rows": [
                                        {
                                            "id": "technical",
                                            "title": "🔧 Technical Issues",
                                            "description": "System faults, inverter errors, panel issue"
                                        },
                                        {
                                            "id": "billing",
                                            "title": "💳 Billing & Payments",
                                            "description": "Invoices, payment plans, refunds"
                                        },
                                        {
                                            "id": "installation",
                                            "title": "🏗️ Installation Support",
                                            "description": "Installation timeline, site visits"
                                        },
                                        {
                                            "id": "product_info",
                                            "title": "📦 Product Information",
                                            "description": "Specs, warranties, compatibility"
                                        },
                                        {
                                            "id": "other",
                                            "title": "📝 Other",
                                            "description": "Anything else we can help with"
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
                        "body": "📝 Please *describe your issue or question* in a few sentences.\n\n"
                               "The more detail you share, the faster we can help!"
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
                            "text": "📞 How should our support team reach you?\n\n"
                                   "Choose your preferred contact method."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "whatsapp", "title": "💬 WhatsApp"}},
                                {"type": "reply", "reply": {"id": "phone_call", "title": "📞 Phone Call"}},
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
        },        # ── Format raw IDs to readable labels ──────────────────────
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
        },        # ── Confirmation with interactive buttons ──────────────────────
        {
            "name": "confirm_support_request",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "💬 Review Support Request"},
                        "body": {
                            "text": "Hi {{customer_name}}, please confirm your support request:\n\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n"
                                   "📋 *Category:* {{support_category}}\n"
                                   "📝 *Details:* {{issue_details}}\n"
                                   "📞 *Contact via:* {{contact_method}}\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                                   "Tap *Submit* to send or *Edit* to start over."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_support", "title": "✅ Submit"}},
                                {"type": "reply", "reply": {"id": "edit_support", "title": "✏️ Edit"}},
                                {"type": "reply", "reply": {"id": "cancel_support", "title": "❌ Cancel"}}
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
                    "body": "✅ *Support request submitted!*\n\n"
                           "Thank you, {{customer_name}}! Here's a summary:\n\n"
                           "📋 Category: {{support_category}}\n"
                           "📞 We'll contact you via: {{contact_method}}\n\n"
                           "Our support team will get back to you within *24 hours*. "
                           "For urgent issues, call us directly at *+263 123 456 789*.\n\n"
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
            "name": "end_cancelled",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "❌ *Support request cancelled.*\n\n"
                           "No problem! You can contact us anytime by typing *support*.\n"
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
