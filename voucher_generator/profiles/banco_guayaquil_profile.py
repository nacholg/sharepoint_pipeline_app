from copy import deepcopy

from voucher_generator.profiles.default_profile import PROFILE_CONFIG as DEFAULT_PROFILE_CONFIG


PROFILE_CONFIG = {
    **deepcopy(DEFAULT_PROFILE_CONFIG),
    "key": "banco_guayaquil",
    "label": "Banco Guayaquil",
    "language": "es",
    "branding": {
        **deepcopy(DEFAULT_PROFILE_CONFIG.get("branding", {})),
        "theme_key": "banco_guayaquil",
        "brand_logo": "assets/logos/banco_guayaquil_logo.png",
    },
}