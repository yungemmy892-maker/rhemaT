import datetime
import html

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

# Hex equivalents of the oklch design tokens in frontend/src/styles.css
# (email clients don't support oklch or CSS custom properties, so the
# palette is hardcoded here to match --primary / --gradient-primary /
# --foreground / --muted-foreground / --border / --background exactly).
BRAND = {
    "bg": "#FAF9FC",
    "surface": "#FFFFFF",
    "border": "#ECE8F2",
    "foreground": "#1F1B2E",
    "muted": "#6B6575",
    "primary": "#A855F7",
    "gradient_start": "#8B5CF6",  # violet-500 — matches the "verse_of_day" tint
    "gradient_end": "#D946EF",  # fuchsia-500
    "radius": "20px",
}

FONT_DISPLAY = "'Fraunces','Cormorant Garamond',Georgia,serif"
FONT_SANS = "'Plus Jakarta Sans',-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"

# Absolute URL to the app's logo glyph (transparent white feather mark),
# served from the frontend's /public directory — email clients can't load
# relative paths or read frontend build assets directly. Only actually
# resolves once FRONTEND_URL points at a real public domain — it'll render
# as a broken image if FRONTEND_URL is still localhost, since email
# clients render server-side and can't reach your local machine.
LOGO_URL = f"{settings.FRONTEND_URL.rstrip('/')}/logo-glyph.png"


def _daily_verse_html(
    name: str, verse_ref: str, verse_text: str, version: str, app_url: str
) -> str:
    b = BRAND
    # M1: user-controlled (settable via registration / Edit Profile), so it
    # must be escaped before landing in an HTML f-string template.
    name = html.escape(name)
    today = datetime.date.today().strftime("%A, %B %-d")
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:{b['bg']};font-family:{FONT_SANS};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{b['bg']};padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;">

            <!-- Logo / wordmark -->
            <tr>
              <td align="center" style="padding-bottom:20px;">
                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td width="40" style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});" align="center" valign="middle">
                      <img src="{LOGO_URL}" width="20" height="20" alt="VerseID" style="display:block;" />
                    </td>
                    <td style="padding-left:10px;font-family:{FONT_DISPLAY};font-size:20px;font-weight:600;color:{b['foreground']};">VerseID</td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Card -->
            <tr>
              <td style="background:{b['surface']};border:1px solid {b['border']};border-radius:{b['radius']};overflow:hidden;">

                <!-- Gradient header -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});padding:26px 32px;">
                      <div style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:rgba(255,255,255,0.8);">
                        Your Daily Verse
                      </div>
                      <div style="font-family:{FONT_DISPLAY};font-size:18px;font-weight:600;color:#ffffff;margin-top:4px;">
                        {today}
                      </div>
                    </td>
                  </tr>
                </table>

                <!-- Verse -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="padding:36px 34px 30px;text-align:center;">
                      <div style="font-family:{FONT_DISPLAY};font-size:44px;line-height:1;color:{b['gradient_start']};opacity:0.35;">&#8220;</div>
                      <div style="font-family:{FONT_DISPLAY};font-size:22px;line-height:1.5;color:{b['foreground']};font-weight:500;margin-top:-14px;">
                        {verse_text}
                      </div>
                      <div style="margin-top:22px;display:inline-block;padding:7px 16px;border-radius:999px;background:{b['bg']};border:1px solid {b['border']};font-size:13px;font-weight:600;color:{b['gradient_start']};">
                        {verse_ref} &middot; {version}
                      </div>
                    </td>
                  </tr>
                </table>

                <!-- CTA -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="padding:0 32px 34px;" align="center">
                      <a href="{app_url}" style="display:inline-block;padding:13px 34px;border-radius:999px;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;">
                        Open VerseID
                      </a>
                      <div style="margin-top:14px;font-size:12.5px;color:{b['muted']};">
                        Tap the app to save this verse or identify another one.
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td align="center" style="padding:22px 12px;font-size:12px;color:{b['muted']};">
                Hi {name} &mdash; you're receiving this because daily verse notifications are on.
                <br/>Turn them off anytime in Settings.
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_daily_verse_email(
    to_email: str, name: str, verse_ref: str, verse_text: str, version: str
):
    app_url = f"{settings.FRONTEND_URL.rstrip('/')}/app/home"
    subject = f"Your verse for today: {verse_ref}"
    text_body = (
        f"Hi {name},\n\n"
        f'"{verse_text}"\n'
        f"— {verse_ref} ({version})\n\n"
        "Open VerseID to save this verse or identify another one.\n"
    )

    msg = EmailMultiAlternatives(subject, text_body, None, [to_email])
    msg.attach_alternative(
        _daily_verse_html(name, verse_ref, verse_text, version, app_url), "text/html"
    )
    msg.send(fail_silently=False)


def _welcome_html(name: str, app_url: str) -> str:
    b = BRAND
    # M1: user-controlled, must be escaped before interpolation.
    name = html.escape(name)
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:{b['bg']};font-family:{FONT_SANS};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{b['bg']};padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;">

            <!-- Logo / wordmark -->
            <tr>
              <td align="center" style="padding-bottom:24px;">
                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td width="40" style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});" align="center" valign="middle">
                      <img src="{LOGO_URL}" width="20" height="20" alt="VerseID" style="display:block;" />
                    </td>
                    <td style="padding-left:10px;font-family:{FONT_DISPLAY};font-size:20px;font-weight:600;color:{b['foreground']};">VerseID</td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Card -->
            <tr>
              <td style="background:{b['surface']};border:1px solid {b['border']};border-radius:{b['radius']};overflow:hidden;">

                <!-- Gradient header -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});padding:36px 32px;" align="center">
                      <div style="font-size:34px;line-height:1;">👋</div>
                      <div style="font-family:{FONT_DISPLAY};font-size:24px;font-weight:600;color:#ffffff;margin-top:12px;">
                        Welcome to VerseID
                      </div>
                    </td>
                  </tr>
                </table>

                <!-- Body -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:28px 32px 32px;">
                  <tr>
                    <td style="font-size:15px;line-height:1.6;color:{b['foreground']};">
                      Hi {name},
                      <br/><br/>
                      Your account is ready. VerseID listens for any Bible verse being read aloud — a
                      sermon, a friend, a memory — and tells you exactly what it is and where it's from.
                    </td>
                  </tr>

                  <tr><td style="height:22px;"></td></tr>

                  <!-- Feature list -->
                  <tr>
                    <td>
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{b['bg']};border-radius:14px;padding:4px 0;">
                        <tr>
                          <td style="padding:14px 18px;font-size:14px;color:{b['foreground']};">🎙️&nbsp;&nbsp;<strong>Identify</strong> — tap the mic and speak, VerseID matches it instantly</td>
                        </tr>
                        <tr>
                          <td style="padding:0 18px 14px;font-size:14px;color:{b['foreground']};">📖&nbsp;&nbsp;<strong>Library</strong> — every verse you find is saved for later</td>
                        </tr>
                        <tr>
                          <td style="padding:0 18px 14px;font-size:14px;color:{b['foreground']};">✨&nbsp;&nbsp;<strong>Daily verse</strong> — a new verse delivered at the time you choose</td>
                        </tr>
                      </table>
                    </td>
                  </tr>

                  <tr><td style="height:26px;"></td></tr>

                  <!-- CTA -->
                  <tr>
                    <td align="center">
                      <a href="{app_url}" style="display:inline-block;padding:13px 32px;border-radius:999px;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;">
                        Open VerseID
                      </a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td align="center" style="padding:22px 12px;font-size:12px;color:{b['muted']};">
                You're receiving this because you created a VerseID account.
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _code_html(name: str, code: str) -> str:
    b = BRAND
    # M1: user-controlled, must be escaped before interpolation.
    name = html.escape(name)
    digits = "".join(
        f'<td style="padding:0 4px;">'
        f'<div style="width:38px;height:48px;line-height:48px;text-align:center;border-radius:10px;'
        f'background:{b["bg"]};border:1px solid {b["border"]};font-family:{FONT_DISPLAY};'
        f'font-size:22px;font-weight:600;color:{b["foreground"]};">{d}</div></td>'
        for d in code
    )
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:{b['bg']};font-family:{FONT_SANS};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{b['bg']};padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:440px;">

            <tr>
              <td align="center" style="padding-bottom:24px;">
                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td width="40" style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});" align="center" valign="middle">
                      <img src="{LOGO_URL}" width="20" height="20" alt="VerseID" style="display:block;" />
                    </td>
                    <td style="padding-left:10px;font-family:{FONT_DISPLAY};font-size:20px;font-weight:600;color:{b['foreground']};">VerseID</td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="background:{b['surface']};border:1px solid {b['border']};border-radius:{b['radius']};padding:36px 32px;text-align:center;">
                <div style="width:52px;height:52px;line-height:52px;text-align:center;border-radius:16px;margin:0 auto;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});font-size:22px;">🔒</div>
                <div style="font-family:{FONT_DISPLAY};font-size:22px;font-weight:600;color:{b['foreground']};margin-top:18px;">
                  Reset your password
                </div>
                <p style="font-size:14px;line-height:1.6;color:{b['muted']};margin:10px 0 26px;">
                  Hi {name}, use this code to finish resetting your VerseID password. It expires in 10 minutes.
                </p>

                <table role="presentation" cellpadding="0" cellspacing="0" align="center">
                  <tr>{digits}</tr>
                </table>

                <p style="font-size:12px;color:{b['muted']};margin-top:26px;">
                  Didn't request this? You can safely ignore this email.
                </p>
              </td>
            </tr>

            <tr>
              <td align="center" style="padding:22px 12px;font-size:12px;color:{b['muted']};">
                VerseID — Find any Bible verse instantly.
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_password_reset_email(to_email: str, name: str, code: str) -> None:
    """
    Sent when a user requests a password reset. Delivers a 6-digit code
    (not a link) since the frontend flow is: email -> enter code -> new
    password, all on one page.
    """
    subject = f"Your VerseID reset code: {code}"
    text_body = (
        f"Hi {name},\n\n"
        f"Your VerseID password reset code is: {code}\n\n"
        "This code expires in 10 minutes. If you didn't request this, "
        "you can safely ignore this email.\n"
    )

    msg = EmailMultiAlternatives(subject, text_body, None, [to_email])
    msg.attach_alternative(_code_html(name, code), "text/html")
    msg.send(fail_silently=False)


def send_welcome_email(to_email: str, name: str) -> None:
    """
    Sent once, immediately after a brand-new account is created — either
    via email/password registration or a user's first-ever Google sign-in.
    Styled to match the app's own purple gradient / Fraunces+Plus Jakarta
    Sans design system rather than a generic transactional template.
    """
    app_url = f"{settings.FRONTEND_URL.rstrip('/')}/app/home"
    subject = "Welcome to VerseID 👋"
    text_body = (
        f"Hi {name},\n\n"
        "Your VerseID account is ready. Point your mic at any verse being read "
        "aloud and we'll tell you exactly what it is and where it's from.\n\n"
        "- Identify: tap the mic and speak, VerseID matches it instantly\n"
        "- Library: every verse you find is saved for later\n"
        "- Daily verse: a new verse delivered at the time you choose\n\n"
        f"Open VerseID: {app_url}\n"
    )

    msg = EmailMultiAlternatives(subject, text_body, None, [to_email])
    msg.attach_alternative(_welcome_html(name, app_url), "text/html")
    msg.send(fail_silently=False)


def _password_changed_html(name: str, headline: str, message: str) -> str:
    b = BRAND
    # M1: user-controlled, must be escaped before interpolation.
    name = html.escape(name)
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:{b['bg']};font-family:{FONT_SANS};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{b['bg']};padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:440px;">

            <tr>
              <td align="center" style="padding-bottom:24px;">
                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td width="40" style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});" align="center" valign="middle">
                      <img src="{LOGO_URL}" width="20" height="20" alt="VerseID" style="display:block;" />
                    </td>
                    <td style="padding-left:10px;font-family:{FONT_DISPLAY};font-size:20px;font-weight:600;color:{b['foreground']};">VerseID</td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="background:{b['surface']};border:1px solid {b['border']};border-radius:{b['radius']};padding:36px 32px;text-align:center;">
                <div style="width:52px;height:52px;line-height:52px;text-align:center;border-radius:16px;margin:0 auto;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});font-size:22px;">🔒</div>
                <div style="font-family:{FONT_DISPLAY};font-size:22px;font-weight:600;color:{b['foreground']};margin-top:18px;">
                  {headline}
                </div>
                <p style="font-size:14px;line-height:1.6;color:{b['muted']};margin:10px 0 4px;">
                  Hi {name}, {message}
                </p>
                <p style="font-size:13px;line-height:1.6;color:{b['foreground']};background:{b['bg']};border:1px solid {b['border']};border-radius:12px;padding:12px 14px;margin-top:22px;">
                  If this wasn't you, please reset your password immediately and contact support.
                </p>
              </td>
            </tr>

            <tr>
              <td align="center" style="padding:22px 12px;font-size:12px;color:{b['muted']};">
                VerseID — Find any Bible verse instantly.
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_password_changed_email(to_email: str, name: str, first_time: bool = False) -> None:
    if first_time:
        subject = "A password was added to your VerseID account"
        headline = "Password added"
        message = (
            "a password was just added to your VerseID account you can now "
            "sign in with your email and password, as well as Google."
        )
    else:
        subject = "Your VerseID password was changed"
        headline = "Password changed"
        message = "your VerseID password was just changed."

    text_body = (
        f"Hi {name},\n\n"
        f"{message[0].upper()}{message[1:]}\n\n"
        "If this wasn't you, please reset your password immediately and "
        "contact support.\n"
    )

    msg = EmailMultiAlternatives(subject, text_body, None, [to_email])
    msg.attach_alternative(
        _password_changed_html(name, headline, message), "text/html"
    )
    msg.send(fail_silently=False)


def _pro_expired_html(name: str, resubscribe_url: str) -> str:
    b = BRAND
    # M1: user-controlled, must be escaped before interpolation.
    name = html.escape(name)
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:{b['bg']};font-family:{FONT_SANS};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{b['bg']};padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:440px;">

            <tr>
              <td align="center" style="padding-bottom:24px;">
                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td width="40" style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});" align="center" valign="middle">
                      <img src="{LOGO_URL}" width="20" height="20" alt="VerseID" style="display:block;" />
                    </td>
                    <td style="padding-left:10px;font-family:{FONT_DISPLAY};font-size:20px;font-weight:600;color:{b['foreground']};">VerseID</td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="background:{b['surface']};border:1px solid {b['border']};border-radius:{b['radius']};padding:36px 32px;text-align:center;">
                <div style="width:52px;height:52px;line-height:52px;text-align:center;border-radius:16px;margin:0 auto;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});font-size:22px;">⏳</div>
                <div style="font-family:{FONT_DISPLAY};font-size:22px;font-weight:600;color:{b['foreground']};margin-top:18px;">
                  Your Pro access has ended
                </div>
                <p style="font-size:14px;line-height:1.6;color:{b['muted']};margin:10px 0 26px;">
                  Hi {name}, the Pro billing period you already paid for has now finished,
                  so your VerseID account is back on the Free plan.
                </p>
                <a href="{resubscribe_url}" style="display:inline-block;padding:13px 32px;border-radius:999px;background:linear-gradient(135deg,{b['gradient_start']},{b['gradient_end']});color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;">
                  Resubscribe to Pro
                </a>
              </td>
            </tr>

            <tr>
              <td align="center" style="padding:22px 12px;font-size:12px;color:{b['muted']};">
                VerseID - Find any Bible verse instantly.
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_pro_expired_email(to_email: str, name: str) -> None:
    resubscribe_url = f"{settings.FRONTEND_URL.rstrip('/')}/app/subscription"
    subject = "Your VerseID Pro access has ended"
    text_body = (
        f"Hi {name},\n\n"
        "The Pro billing period you already paid for has now finished, so your "
        "VerseID account is back on the Free plan.\n\n"
        f"Resubscribe any time: {resubscribe_url}\n"
    )

    msg = EmailMultiAlternatives(subject, text_body, None, [to_email])
    msg.attach_alternative(_pro_expired_html(name, resubscribe_url), "text/html")
    msg.send(fail_silently=False)
