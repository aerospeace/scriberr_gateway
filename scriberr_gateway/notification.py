from __future__ import annotations

import apprise

from .config import AppriseConfig


def send_notification(config: AppriseConfig, title: str, body: str) -> None:
    notifier = apprise.Apprise()
    notifier.add(config.url)
    notifier.notify(title=title, body=body)
    # if config.tag:
    #     notifier.notify(title=title, body=body, tag=config.tag)
    # else:
