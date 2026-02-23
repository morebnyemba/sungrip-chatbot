# backend/flows/definitions/main_menu_flow_sn.py

"""
Main menu flow definition — Shona version.

Shona translation of the main menu that greets users and routes them
to the appropriate sub-flow via WhatsApp interactive list messages.
"""

MAIN_MENU_FLOW_SN = {
    "name": "main_menu_sn",
    "friendly_name": "Main Menu (Shona)",
    "description": "Shona main menu — inopa vashandisi sarudzo dzemasevhisi neShona",
    "is_active": True,
    "trigger_keywords": ["menyu", "tanga", "mhoro", "ndeipi", "batsira", "sarudzo"],
    "steps": [
        # Step 1: Ensure customer profile exists
        {
            "name": "ensure_customer_profile_exists",
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
                    "to_step": "show_main_menu",
                    "condition_config": {"type": "auto"},
                    "priority": 1
                }
            ]
        },
        # Step 2: Show interactive list menu with Shona greeting
        {
            "name": "show_main_menu",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {
                            "type": "text",
                            "text": "☀️ Sungrip Solar"
                        },
                        "body": {
                            "text": "Mhoro {{customer_name}}, mauya ku *Sungrip Solar* — "
                                    "shamwari yenyu yemasolar muZimbabwe.\n\n"
                                    "🔋 *Zvatinopa:*\n"
                                    "1️⃣ Masolar system pachikafu — bhadhara kadiki mushure mekuiswa, "
                                    "kuendeswa nekuiswa zvakabatanidzwa. Shandisai iye zvino, "
                                    "mobhadhara gare gare!\n"
                                    "2️⃣ Masolar system ane mawarranty agreement neresiti\n"
                                    "3️⃣ Rubatsiro rwegore mushure mekuiswa\n"
                                    "4️⃣ Maquote emahara nekukurukura pamasolar makuru "
                                    "(6.2 kVA+ kusvika kumasolar farm)\n\n"
                                    "Dzvanyai bhatani riri pasi kuti muone masevhisi edu 👇"
                        },
                        "footer": {
                            "text": "Powered by slykertech.co.zw"
                        },
                        "action": {
                            "button": "📋 Onai Sarudzo",
                            "sections": [
                                {
                                    "title": "Masolar Solutions",
                                    "rows": [
                                        {
                                            "id": "view_packages",
                                            "title": "🔆 Masolar Packages",
                                            "description": "Enzanisai mapackage emasolar edu nemutengo"
                                        },
                                        {
                                            "id": "shop_products",
                                            "title": "🛒 Tengai Zvinhu",
                                            "description": "Onai zviwanikwa zvezuva zvese"
                                        },
                                        {
                                            "id": "request_quote",
                                            "title": "📋 Wanai Quote Mahara",
                                            "description": "Munoda system yakasiyana? Tichakuitirai"
                                        },
                                        {
                                            "id": "schedule_installation",
                                            "title": "📅 Bukurai Kuiswa",
                                            "description": "Sarudzai zuva rakanakira kuiswa kwenyu"
                                        }
                                    ]
                                },
                                {
                                    "title": "Rubatsiro",
                                    "rows": [
                                        {
                                            "id": "contact_support",
                                            "title": "💬 Batai Tirimu",
                                            "description": "Taurai netirimu yedu pamibvunzo yese"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "expected_type": "interactive_id",
                    "save_to_variable": "menu_choice"
                }
            },
            "transitions": [
                {
                    "to_step": "route_to_packages",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "view_packages"
                    },
                    "priority": 1
                },
                {
                    "to_step": "route_to_catalog",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "shop_products"
                    },
                    "priority": 2
                },
                {
                    "to_step": "route_to_quote",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "request_quote"
                    },
                    "priority": 3
                },
                {
                    "to_step": "route_to_installation",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "schedule_installation"
                    },
                    "priority": 4
                },
                {
                    "to_step": "route_to_support",
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "contact_support"
                    },
                    "priority": 5
                },
                {
                    "to_step": "show_main_menu",
                    "condition_config": {"type": "always_true"},
                    "priority": 6
                }
            ]
        },
        # Route steps — switch to Shona sub-flows
        {
            "name": "route_to_quote",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "solar_quote_request_sn",
                "message": "Zvakanaka! Regai ndikubatsireyi kuwana quote. 📋",
                "initial_context_template": {}
            },
            "transitions": []
        },
        {
            "name": "route_to_installation",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "installation_scheduling_sn",
                "message": "Zvakanaka! Ngatibukurei kuiswa kwenyu. 📅",
                "initial_context_template": {}
            },
            "transitions": []
        },
        {
            "name": "route_to_packages",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "solar_packages_sn",
                "message": "Regai ndikuratidzei mapackage emasolar atiinawo. 📦",
                "initial_context_template": {}
            },
            "transitions": []
        },
        {
            "name": "route_to_catalog",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "send_catalog_message",
                        "params_template": {
                            "body_text": "🛒 *Sungrip Solar — Zviwanikwa*\n\nOnai zviwanikwa zvedu pazasi. Isai zvinhu mungoro yenyu modzvanya *Tumira* kuti muise order — tichaisimbisa pano paWhatsApp!",
                            "footer_text": "Dzvanyai pachigadzirwa kuti muone zvakawanda"
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "end_after_catalog",
                    "condition_config": {"type": "always_true"},
                    "priority": 1
                }
            ]
        },
        {
            "name": "end_after_catalog",
            "type": "end_flow",
            "config": {},
            "transitions": []
        },
        {
            "name": "route_to_support",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "contact_support_sn",
                "message": "Ndichakubatanidzai netirimu yedu yerubatsiro. 👥",
                "initial_context_template": {}
            },
            "transitions": []
        }
    ]
}
