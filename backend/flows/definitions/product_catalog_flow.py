# backend/flows/definitions/product_catalog_flow.py

"""
Product catalog browsing & ordering flow definition.

Lets WhatsApp users shop individual products by category, view full
details, and either place an order (with quantity) or send an enquiry.

Every "Order Now" and "Enquire" action persists a ProductOrder record
in the database so the sales team can follow up.

Flow paths:
  Browse  → categories → products → details
  Order   → quantity → confirm → save_product_order → confirmation
  Enquire → save_product_enquiry → confirmation
"""

PRODUCT_CATALOG_FLOW = {
    "name": "product_catalog",
    "friendly_name": "Shop Products",
    "description": "Browse and shop individual solar products by category (DB-driven, orders persisted)",
    "is_active": True,
    "trigger_keywords": [
        "shop", "products", "buy", "catalog", "catalogue",
        "browse", "equipment", "parts", "individual",
    ],
    "steps": [
        # ── Step 1: Build interactive category list ────────────────────
        {
            "name": "build_categories",
            "type": "action",
            "is_entry_point": True,
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "build_product_categories_list",
                        "parameters": {},
                    },
                    {
                        "action_type": "send_dynamic_message",
                        "parameters": {"message_variable": "_categories_list_msg"},
                    },
                ],
            },
            "transitions": [
                {
                    "to_step": "capture_category",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },
        # ── Step 2: Wait for category selection ────────────────────────
        {
            "name": "capture_category",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "👆 Tap *Browse Categories* above, then select a category."
                    },
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "selected_category",
                },
            },
            "transitions": [
                {
                    "to_step": "build_products",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },
        # ── Step 3: Build products for selected category ───────────────
        {
            "name": "build_products",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "build_products_interactive_list",
                        "parameters": {
                            "category_variable": "selected_category",
                        },
                    },
                    {
                        "action_type": "send_dynamic_message",
                        "parameters": {"message_variable": "_products_list_msg"},
                    },
                ],
            },
            "transitions": [
                {
                    "to_step": "capture_product",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },
        # ── Step 4: Wait for product selection ─────────────────────────
        {
            "name": "capture_product",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "👆 Tap *View Products* above to browse, then select a product for full details."
                    },
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "selected_product",
                },
            },
            "transitions": [
                {
                    "to_step": "load_product_details",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },
        # ── Step 5: Fetch product details ──────────────────────────────
        {
            "name": "load_product_details",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "fetch_product_details",
                        "parameters": {
                            "selection_variable": "selected_product",
                        },
                    },
                ],
            },
            "transitions": [
                {
                    "to_step": "show_product_details",
                    "condition_config": {
                        "type": "expression",
                        "expression": "product_found == True",
                    },
                    "priority": 1,
                },
                {
                    "to_step": "build_products",
                    "condition_config": {"type": "always_true"},
                    "priority": 2,
                },
            ],
        },
        # ── Step 6: Display product details ────────────────────────────
        {
            "name": "show_product_details",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "{{product_detail_text}}"
                },
            },
            "transitions": [
                {
                    "to_step": "product_action",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },
        # ── Step 7: What next? — Order / Enquire / Browse ─────────────
        {
            "name": "product_action",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "What would you like to do?"
                        },
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {"id": "order_now", "title": "🛒 Order Now"},
                                },
                                {
                                    "type": "reply",
                                    "reply": {"id": "enquire_product", "title": "💬 Enquire"},
                                },
                                {
                                    "type": "reply",
                                    "reply": {"id": "view_another_product", "title": "🔄 View Another"},
                                },
                            ],
                        },
                    },
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "product_next_action",
                },
            },
            "transitions": [
                {
                    "to_step": "ask_quantity",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "order_now",
                    },
                    "priority": 1,
                },
                {
                    "to_step": "save_enquiry",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "enquire_product",
                    },
                    "priority": 2,
                },
                {
                    "to_step": "build_categories",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "view_another_product",
                    },
                    "priority": 3,
                },
                {
                    "to_step": "thank_you",
                    "condition_config": {"type": "always_true"},
                    "priority": 4,
                },
            ],
        },

        # ═══════════════════════════════════════════════════════════════
        # ORDER PATH
        # ═══════════════════════════════════════════════════════════════

        # ── Step 8: Ask quantity ───────────────────────────────────────
        {
            "name": "ask_quantity",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": (
                            "How many *{{product_name}}* would you like to order?\n\n"
                            "Reply with a number (e.g. *1*, *2*, *5*)."
                        ),
                    },
                },
                "reply_config": {
                    "expected_type": "number",
                    "save_to_variable": "order_quantity",
                    "validation": {"min": 1, "max": 100},
                },
            },
            "transitions": [
                {
                    "to_step": "ask_delivery_method",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },

        # ── Step 8b: Delivery method ──────────────────────────────────
        {
            "name": "ask_delivery_method",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": (
                                "🚚 How would you like to receive your order?"
                            ),
                        },
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {"id": "delivery", "title": "🚚 Delivery"},
                                },
                                {
                                    "type": "reply",
                                    "reply": {"id": "collection", "title": "🏪 Collection"},
                                },
                            ],
                        },
                    },
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "delivery_method",
                },
            },
            "transitions": [
                {
                    "to_step": "ask_delivery_name",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "delivery",
                    },
                    "priority": 1,
                },
                {
                    "to_step": "ask_delivery_name",
                    "condition_config": {"type": "always_true"},
                    "priority": 2,
                },
            ],
        },

        # ── Step 8c: Delivery name ────────────────────────────────────
        {
            "name": "ask_delivery_name",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "👤 What is the *full name* for this order?",
                    },
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "delivery_name",
                },
            },
            "transitions": [
                {
                    "to_step": "ask_delivery_phone",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },

        # ── Step 8d: Delivery phone ───────────────────────────────────
        {
            "name": "ask_delivery_phone",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": (
                            "📱 What is the best *contact number* for this order?\n\n"
                            "_e.g. +263 77 123 4567_"
                        ),
                    },
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "delivery_phone",
                },
            },
            "transitions": [
                {
                    "to_step": "ask_delivery_address",
                    "condition_config": {
                        "type": "expression",
                        "expression": "delivery_method == 'delivery'",
                    },
                    "priority": 1,
                },
                {
                    "to_step": "confirm_order",
                    "condition_config": {"type": "always_true"},
                    "priority": 2,
                },
            ],
        },

        # ── Step 8e: Delivery address (only for delivery) ─────────────
        {
            "name": "ask_delivery_address",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": (
                            "📍 Please provide the *full delivery address*.\n\n"
                            "Be as specific as possible — include suburb, "
                            "city, and any landmarks."
                        ),
                    },
                },
                "reply_config": {
                    "expected_type": "text",
                    "save_to_variable": "delivery_address",
                },
            },
            "transitions": [
                {
                    "to_step": "confirm_order",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },

        # ── Step 9: Confirm order before placing ───────────────────────
        {
            "name": "confirm_order",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "📋 Confirm Your Order"},
                        "body": {
                            "text": (
                                "Please confirm your order:\n\n"
                                "━━━━━━━━━━━━━━━━━━━━\n"
                                "📦 *Product:* {{product_name}}\n"
                                "🔢 *Quantity:* {{order_quantity}}\n"
                                "💰 *Unit Price:* {{product_price_display}}\n"
                                "━━━━━━━━━━━━━━━━━━━━\n"
                                "👤 *Name:* {{delivery_name}}\n"
                                "📱 *Phone:* {{delivery_phone}}\n"
                                "🚚 *Method:* {{delivery_method}}\n"
                                "📍 *Address:* {{delivery_address}}\n"
                                "━━━━━━━━━━━━━━━━━━━━\n\n"
                                "Would you like to place this order?"
                            ),
                        },
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {"id": "yes_place_order", "title": "✅ Place Order"},
                                },
                                {
                                    "type": "reply",
                                    "reply": {"id": "no_go_back", "title": "🔙 Go Back"},
                                },
                            ],
                        },
                    },
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "order_confirmation",
                },
            },
            "transitions": [
                {
                    "to_step": "place_order",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "yes_place_order",
                    },
                    "priority": 1,
                },
                {
                    "to_step": "product_action",
                    "condition_config": {"type": "always_true"},
                    "priority": 2,
                },
            ],
        },
        # ── Step 10: Save order to database ────────────────────────────
        {
            "name": "place_order",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "save_product_order",
                        "parameters": {},
                    },
                    {
                        "action_type": "send_group_notification",
                        "parameters": {
                            "group_names": ["Sales Team"],
                            "template_name": "sungrip_new_product_order",
                        },
                    },
                ],
            },
            "transitions": [
                {
                    "to_step": "order_success",
                    "condition_config": {
                        "type": "expression",
                        "expression": "order_saved == True",
                    },
                    "priority": 1,
                },
                {
                    "to_step": "order_failed",
                    "condition_config": {"type": "always_true"},
                    "priority": 2,
                },
            ],
        },
        # ── Step 11: Order success ─────────────────────────────────────
        {
            "name": "order_success",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": (
                        "✅ *Order Placed Successfully!*\n\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "🧾 *Reference:* {{order_number}}\n"
                        "📦 *Product:* {{product_name}}\n"
                        "🔢 *Qty:* {{order_quantity}}\n"
                        "💰 *Total:* {{order_total_display}}\n"
                        "👤 *Name:* {{delivery_name}}\n"
                        "🚚 *Delivery:* {{delivery_method}}\n"
                        "━━━━━━━━━━━━━━━━━━━━\n\n"
                        "Our team will contact you shortly to arrange "
                        "payment and delivery.\n\n"
                        "📞 WhatsApp: 0782 233 111 / 0777 139 159"
                    ),
                },
            },
            "transitions": [
                {
                    "to_step": "after_order",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },
        # ── Step 12: Order failed ──────────────────────────────────────
        {
            "name": "order_failed",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": (
                        "⚠️ Sorry, we couldn't place your order right now.\n\n"
                        "Please try again or contact our team directly:\n"
                        "📞 WhatsApp: 0782 233 111 / 0777 139 159"
                    ),
                },
            },
            "transitions": [
                {
                    "to_step": "after_order",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },
        # ── Step 13: After order — continue or exit ────────────────────
        {
            "name": "after_order",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "Would you like to continue shopping?"},
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {"id": "keep_shopping", "title": "🛒 Keep Shopping"},
                                },
                                {
                                    "type": "reply",
                                    "reply": {"id": "main_menu", "title": "🏠 Main Menu"},
                                },
                            ],
                        },
                    },
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "after_order_choice",
                },
            },
            "transitions": [
                {
                    "to_step": "build_categories",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "keep_shopping",
                    },
                    "priority": 1,
                },
                {
                    "to_step": "thank_you",
                    "condition_config": {"type": "always_true"},
                    "priority": 2,
                },
            ],
        },

        # ═══════════════════════════════════════════════════════════════
        # ENQUIRY PATH
        # ═══════════════════════════════════════════════════════════════

        # ── Step 14: Save enquiry to database ──────────────────────────
        {
            "name": "save_enquiry",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "save_product_enquiry",
                        "parameters": {},
                    },
                    {
                        "action_type": "send_group_notification",
                        "parameters": {
                            "group_names": ["Sales Team"],
                            "template_name": "sungrip_new_product_enquiry",
                        },
                    },
                ],
            },
            "transitions": [
                {
                    "to_step": "enquiry_confirmation",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },
        # ── Step 15: Enquiry saved confirmation ────────────────────────
        {
            "name": "enquiry_confirmation",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": (
                        "📩 *Enquiry Received!*\n\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "🧾 *Ref:* {{enquiry_reference}}\n"
                        "📦 *Product:* {{product_name}}\n"
                        "💰 *Price:* {{product_price_display}}\n"
                        "━━━━━━━━━━━━━━━━━━━━\n\n"
                        "Our sales team will reach out to you shortly.\n"
                        "In the meantime, feel free to keep browsing.\n\n"
                        "📞 WhatsApp: 0782 233 111 / 0777 139 159"
                    ),
                },
            },
            "transitions": [
                {
                    "to_step": "after_order",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },

        # ═══════════════════════════════════════════════════════════════
        # END
        # ═══════════════════════════════════════════════════════════════

        {
            "name": "thank_you",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": (
                        "Thank you for browsing our products! 🌞\n\n"
                        "If you have any questions, message us anytime.\n"
                        "Type *menu* to return to the main menu."
                    ),
                },
            },
            "transitions": [
                {
                    "to_step": "end",
                    "condition_config": {"type": "auto"},
                    "priority": 1,
                },
            ],
        },
        {
            "name": "end",
            "type": "end_flow",
            "config": {},
        },
    ],
}
