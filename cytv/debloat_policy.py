"""Fixed groups and LG setting values shared by the host and on-TV setup."""

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
        ('lmt', 'general', 'Limit ad tracking', 'on'),
    )),
    ('Tips and notifications', (
        ('aiNudge', 'general', 'Turn off Smart Tips', 'off'),
        ('sportsAlarm', 'general', 'Turn off sports notifications', 'off'),
    )),
)
SETTINGS = {
    key: (category, label, target)
    for _, rows in GROUPS for key, category, label, target in rows
}
