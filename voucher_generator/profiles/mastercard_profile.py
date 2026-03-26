from voucher_generator.profiles.default_profile import PROFILE_CONFIG as DEFAULT_PROFILE_CONFIG

PROFILE_CONFIG = {
    **DEFAULT_PROFILE_CONFIG,
    "key": "mastercard",
    "label": "Mastercard",
    "branding": {
        "theme_key": "mastercard",
        "brand_logo": "assets/logos/MASTERCARD.png",
    },
}