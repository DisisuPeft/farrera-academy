from django.utils import timezone
from django.utils.formats import date_format

def get_today():
    return timezone.now()


def get_formatted_short_date():
    return date_format(
        get_today(),
        format='SHORT_DATE_FORMAT',
        use_l10n=True
    )


def get_date():
    return timezone.now().date()