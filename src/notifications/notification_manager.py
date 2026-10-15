"""Notification manager for in-app and browser-based alerts."""

from __future__ import annotations


class NotificationManager:
    """Store and surface alerts in the UI."""

    def __init__(self):
        self.alerts = []

    def add_alert(self, alert):
        self.alerts.insert(0, alert)
        return alert

    def get_recent_alerts(self, limit=10):
        return self.alerts[:limit]

    def get_unread_count(self):
        return len(self.alerts)
