def load_json_profiles():
    from voucher_generator.profiles import get_profile_config, list_profile_configs

    # Load all profiles to ensure they are registered
    list_profile_configs()