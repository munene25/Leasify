from config.env import env

MPESA = {
    # URLS
    "AUTHENTICATE_URL": env.str("MPESA_AUTHENTICATE_URL"),
    "INITIATE_URL": env.str("MPESA_EXPRESS_URL_INITIATE"),
    "QUERY_URL": env.str("MPESA_EXPRESS_URL_QUERY"),

    # SECRETS
    "CONSUMER_KEY": env.str("MPESA_CONSUMER_KEY"),
    "CONSUMER_SECRET": env.str("MPESA_CONSUMER_SECRET"),
    "SHORTCODE": env.str("MPESA_SHORTCODE"),
    "PASSKEY": env.str("MPESA_PASSKEY"),
}
