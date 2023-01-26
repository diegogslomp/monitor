class Status:
    DEFAULT = 0
    SUCCESS = 1
    INFO = 2
    WARNING = 3
    DANGER = 4
    STATUS_CHOICES = (
        (DEFAULT, "secondary"),
        (SUCCESS, "positive"),
        (INFO, "primary"),
        (WARNING, "warning"),
        (DANGER, "negative"),
    )
