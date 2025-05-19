from config.settings import settings

class RuntimeSettings:
    """
    Manages runtime-configurable settings.
    """
    # Initialize with the default value from config.settings
    current_dry_run_status: bool = settings.DRY_RUN

    @classmethod
    def get_dry_run_status(cls) -> bool:
        """
        Returns the current DRY_RUN status.
        """
        return cls.current_dry_run_status

    @classmethod
    def set_dry_run_status(cls, status: bool) -> None:
        """
        Sets the DRY_RUN status.
        """
        cls.current_dry_run_status = status