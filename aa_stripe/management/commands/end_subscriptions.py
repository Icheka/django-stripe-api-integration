# -*- coding: utf-8 -*-
import sys
import traceback
from time import sleep

from django.core.management.base import BaseCommand

from aa_stripe.models import StripeSubscription

try:
    from raven.contrib.django.raven_compat.models import client
    from django.conf import settings
    settings.RAVEN_CONFIG["dsn"]
    if settings.RAVEN_CONFIG["dsn"] != "":
        sentry_available = True
except (KeyError, NameError, ImportError):
    sentry_available = False


class Command(BaseCommand):
    """
    Terminates outdated subscriptions at period end.

    Should be run hourly.
    Exceptions are queued and returned at the end.
    """

    help = "Terminate outdated subscriptions"

    def handle(self, *args, **options):
        subscriptions = StripeSubscription.get_subcriptions_for_cancel()
        exceptions = []
        for subscription in subscriptions:
            try:
                subscription.cancel(at_period_end=True)
                sleep(0.25)  # 4 requests per second tops
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if sentry_available:
                    client.captureException()
                else:
                    exceptions.append({
                        "obj": subscription,
                        "exc_type": exc_type,
                        "exc_value": exc_value,
                        "exc_traceback": exc_traceback,
                    })

        for e in exceptions:
            print("Exception happened")
            print("Subscription id: {obj.id}".format(obj=e["obj"]))
            traceback.print_exception(e["exc_type"], e["exc_value"], e["exc_traceback"], file=sys.stdout)
        if exceptions:
            sys.exit(1)
