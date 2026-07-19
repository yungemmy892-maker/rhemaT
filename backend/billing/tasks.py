from celery import shared_task
from django.core.management import call_command


@shared_task(name="billing.tasks.charge_renewals")
def charge_renewals():
    call_command("charge_renewals")