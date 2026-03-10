class PgBackupManagerError(Exception):
    """Базовая ошибка проекта."""


class ValidationError(PgBackupManagerError):
    """Ошибка валидации пользовательских данных."""


class ConfigError(PgBackupManagerError):
    """Ошибка чтения или записи конфигурации."""


class BackupExecutionError(PgBackupManagerError):
    """Ошибка выполнения резервного копирования."""


class SchedulerError(PgBackupManagerError):
    """Ошибка интеграции с Планировщиком задач."""