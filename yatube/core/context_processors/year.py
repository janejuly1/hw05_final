from django.utils import timezone


def year(request):
    """Добавляет переменную с текущим годом."""
    today_year = int(timezone.now().year)
    return {
        'year': today_year,
    }
