"""Package graphics resolution from the TV's explicit UHD capability."""
URI = 'com.webos.service.tv.systemproperty/getSystemInfo'


def resolution(info):
    if isinstance(info, dict) and info.get('returnValue') is True:
        value = info.get('UHD')
        if value is True or type(value) is str and value == 'true':
            return '1920x1080'
        if value is False or type(value) is str and value == 'false':
            return '1280x720'
    raise ValueError('TV graphics capability could not be verified')
