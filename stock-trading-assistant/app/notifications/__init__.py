"""
Notification modules
"""
from app.notifications.email import EmailSender, get_email_sender

__all__ = ["EmailSender", "get_email_sender"]
