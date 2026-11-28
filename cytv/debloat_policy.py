"""Fixed groups and LG setting values shared by the host and on-TV setup."""

LOG_UPLOADS = ('dbgLogUpload', 'faultLogUpload')

GROUPS = (
    ('LG Home', (
        ('homePromotion', 'general', 'Turn off sponsored tiles', 'off'),
        ('contentRecommendation', 'other', 'Turn off content recommendations', 'off'),
    )),
    ('Ads and promotions', (
        ('screenSaverAd', 'general', 'Turn off screen saver ads', 'off'),
        ('livePromotion', 'option', 'Turn off promotions while watching', 'off'),
        ('promotionStreamer', 'option', 'Turn off LG promotional streams', 'off'),
        ('webOSPromotionVideo', 'option', 'Turn off webOS promotional video', 'off'),
    )),
    ('Privacy', (
        ('livePlus', 'option', 'Turn off Live Plus', 'off'),
        ('adCookie', 'general', 'Turn off advertising cookies', 'off'),
        ('dbgLogUpload', 'option', 'Turn off debug log uploads to LG', False),
        ('faultLogUpload', 'option', 'Turn off fault log uploads to LG', False),
        ('lmt', 'general', 'Limit ad tracking', 'on'),
    )),
    ('Tips and notifications', (
        ('aiNudge', 'general', 'Turn off Smart Tips', 'off'),
        ('sportsAlarm', 'general', 'Turn off sports notifications', 'off'),
    )),
)

# Stable manual-guide anchors, including the optional log upload switches.
GUIDE_SECTIONS = {
    'homePromotion': 'home-promotions',
    'contentRecommendation': 'home-promotions',
    'screenSaverAd': 'screensaver',
    'livePromotion': 'live-promotions',
    'promotionStreamer': 'live-promotions',
    'webOSPromotionVideo': 'live-promotions',
    'livePlus': 'viewing',
    'adCookie': 'advertising',
    'lmt': 'advertising',
    'aiNudge': 'tips',
    'sportsAlarm': 'sports',
    'dbgLogUpload': 'log-uploads',
    'faultLogUpload': 'log-uploads',
}


def guide_section(key, status):
    if status in ('write-rejected', 'firmware-blocked', 'restore-rejected'):
        return GUIDE_SECTIONS.get(key)


SETTINGS = {
    key: (category, label, target)
    for _, rows in GROUPS for key, category, label, target in rows
}


def valid_value(key, value):
    if key in LOG_UPLOADS:
        return type(value) is bool
    return value in ('on', 'off')


def valid_record(key, entry):
    target = SETTINGS[key][2]
    return (isinstance(entry, dict)
            and valid_value(key, entry.get('target')) and entry['target'] == target
            and valid_value(key, entry.get('original')) and entry['original'] != target)
