# =============================================================================
# emailer.py — Send the email via Gmail SMTP
# =============================================================================
# Think of this file as the delivery driver.
# It takes a finished message and gets it to your inbox.
#
# SMTP = Simple Mail Transfer Protocol — the standard for sending email.
# Gmail requires TLS encryption on port 587, which we set up below.
#
# If you ever want to switch providers (SendGrid, AWS SES, Mailgun),
# this is the ONLY file you'd need to rewrite. Everything else stays the same.
# =============================================================================

import smtplib
from email.mime.text      import MIMEText
from email.mime.multipart import MIMEMultipart

import config


def send_email(to, subject, body):
    """
    Send a plain-text email from the configured Gmail account.

    Parameters:
        to      — recipient email address
        subject — email subject line
        body    — the plain-text email body (built by formatter.py)
    """

    # Build the email message object
    msg             = MIMEMultipart()
    msg["From"]     = config.SENDER_EMAIL
    msg["To"]       = to
    msg["Subject"]  = subject
    msg.attach(MIMEText(body, "plain"))

    # Connect to Gmail's SMTP server and send
    # `with` ensures the connection is always closed cleanly, even on errors
    with smtplib.SMTP("smtp.gmail.com", port=587) as server:
        server.ehlo()       # introduce ourselves to the server
        server.starttls()   # upgrade to an encrypted connection
        server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
        server.sendmail(config.SENDER_EMAIL, to, msg.as_string())

    print(f"  ✓ Email sent to {to}")
