class NotificationService:

    def send(
        self,
        recipient: str,
        message: str,
    ) -> bool:

        raise NotImplementedError


class FakeNotificationService:

    def send(
        self,
        recipient: str,
        message: str,
    ) -> bool:

        return True
