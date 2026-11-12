"""Dates for the fixed challenge scenario and its reporting period."""
from datetime import date, timedelta

from django.conf import settings


def scenario_date():
    return date.fromisoformat(settings.DEMO_AS_OF_DATE)


def latest_data_date():
    return scenario_date() - timedelta(days=1)


def default_reporting_period():
    """Use the last fully closed month available on the challenge demo date."""
    period_end = scenario_date().replace(day=1) - timedelta(days=1)
    return period_end.replace(day=1), period_end
