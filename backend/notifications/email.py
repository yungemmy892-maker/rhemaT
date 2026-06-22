from django.core.mail import send_mail


def send_daily_verse_email(to_email: str, name: str, verse_ref: str, verse_text: str, version: str):
    subject = f"Your verse for today: {verse_ref}"
    message = (
        f"Hi {name},\n\n"
        f'"{verse_text}"\n'
        f"— {verse_ref} ({version})\n\n"
        "Open VerseID to save this verse or identify another one.\n"
    )
    send_mail(subject, message, None, [to_email], fail_silently=False)
