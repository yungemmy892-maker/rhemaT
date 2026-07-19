from celery import shared_task
from django.core.management import call_command


@shared_task(name="notifications.tasks.send_daily_verse")
def send_daily_verse():
    call_command("send_daily_verse")