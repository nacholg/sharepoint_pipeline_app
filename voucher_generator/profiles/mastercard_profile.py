from __future__ import annotations

from voucher_generator.profiles.utils import deep_merge_dict
from voucher_generator.profiles.default_profile import PROFILE_CONFIG as DEFAULT_PROFILE_CONFIG


PROFILE_CONFIG = deep_merge_dict(
    DEFAULT_PROFILE_CONFIG,
    {
        "key": "mastercard",
        "label": "Mastercard",
        "language": "es",
        "branding": {
            "theme_key": "mastercard",
            "brand_logo": "assets/logos/MASTERCARD.png",
        },
    },
)