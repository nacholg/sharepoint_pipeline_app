from voucher_generator.profiles.utils import deep_merge_dict
from voucher_generator.profiles.default_profile import PROFILE_CONFIG as DEFAULT_PROFILE_CONFIG

PROFILE_CONFIG = deep_merge_dict(
    DEFAULT_PROFILE_CONFIG,
    {
        "key": "client_demo",
        "label": "Client Demo",
        "branding": {
            "theme_key": "default",
            "brand_logo": "assets/logos/CLIENT_DEMO.png",
        },
        "copy": {
            "voucher_kicker": "Event Voucher",
            "footer_note": "Please verify all operational details before sending the final document.",
        },
        "rendering": {
            "header_mode": "event_destination",
            "show_hotel_logo": True,
        },
    },
)