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
        # ── WhatsApp Flow integration entry point ──────────────────────
        {
            "name": "check_whatsapp_flow",
            "is_entry_point": True,
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
                    "to_step": "confirm_support",
                    "priority": 1,
                    "condition_config": {"type": "whatsapp_flow_response_received"}
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
                        "header": {"type": "text", "text": "💬 Review Support Request"},
                        "body": {
                            "text": "Please confirm your support request:\n\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n"
                                   "📋 *Category:* {{support_category}}\n"
                                   "📝 *Details:* {{issue_details}}\n"
                                   "📞 *Contact via:* {{contact_method}}\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                                   "Tap *Submit* to send your request."
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_support", "title": "✅ Submit"}},
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
                    "to_step": "confirm_support",
                    "priority": 1,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "confirm_support"
                    }
                },
                {
                    "to_step": "end_cancelled",
                    "priority": 2,
                    "condition_config": {"type": "always_true"}
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
