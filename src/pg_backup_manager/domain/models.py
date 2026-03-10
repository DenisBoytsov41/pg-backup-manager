from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ScheduleType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    DISABLED = "disabled"


@dataclass(slots=True)
class PostgresSettings:
    host: str = "localhost"
    port: int = 5432
    databases: list[str] = field(default_factory=list)
    user: str = "postgres"
    password: str = ""
    pg_dump_path: str = ""
    pg_dumpall_path: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PostgresSettings":
        databases = data.get("databases", [])
        if isinstance(databases, str):
            databases = [databases]

        return cls(
            host=data.get("host", "localhost"),
            port=int(data.get("port", 5432)),
            databases=[str(item).strip() for item in databases if str(item).strip()],
            user=data.get("user", "postgres"),
            password=data.get("password", ""),
            pg_dump_path=data.get("pg_dump_path", ""),
            pg_dumpall_path=data.get("pg_dumpall_path", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BackupSettings:
    backup_dir: str = ""
    retention_days: int = 30
    dump_globals: bool = True
    naming_pattern: str = "{database}_{timestamp}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupSettings":
        return cls(
            backup_dir=data.get("backup_dir", ""),
            retention_days=int(data.get("retention_days", 30)),
            dump_globals=bool(data.get("dump_globals", True)),
            naming_pattern=data.get("naming_pattern", "{database}_{timestamp}"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LoggingSettings:
    main_log_name: str = "backup.log"
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoggingSettings":
        return cls(
            main_log_name=data.get("main_log_name", "backup.log"),
            log_level=data.get("log_level", "INFO"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SchedulerSettings:
    enabled: bool = False
    task_name: str = ""
    schedule_type: ScheduleType = ScheduleType.DISABLED
    start_time: str = "02:00"
    days_of_week: list[str] = field(default_factory=list)
    run_user: str = ""
    run_with_highest_privileges: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SchedulerSettings":
        raw_schedule_type = data.get("schedule_type", ScheduleType.DISABLED.value)
        try:
            schedule_type = ScheduleType(raw_schedule_type)
        except ValueError:
            schedule_type = ScheduleType.DISABLED

        return cls(
            enabled=bool(data.get("enabled", False)),
            task_name=data.get("task_name", ""),
            schedule_type=schedule_type,
            start_time=data.get("start_time", "02:00"),
            days_of_week=[str(day).strip() for day in data.get("days_of_week", []) if str(day).strip()],
            run_user=data.get("run_user", ""),
            run_with_highest_privileges=bool(data.get("run_with_highest_privileges", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schedule_type"] = self.schedule_type.value
        return data


@dataclass(slots=True)
class BackupProfile:
    schema_version: int = 1
    profile_name: str = "Default Profile"
    postgres: PostgresSettings = field(default_factory=PostgresSettings)
    backup: BackupSettings = field(default_factory=BackupSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    scheduler: SchedulerSettings = field(default_factory=SchedulerSettings)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupProfile":
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            profile_name=data.get("profile_name", "Default Profile"),
            postgres=PostgresSettings.from_dict(data.get("postgres", {})),
            backup=BackupSettings.from_dict(data.get("backup", {})),
            logging=LoggingSettings.from_dict(data.get("logging", {})),
            scheduler=SchedulerSettings.from_dict(data.get("scheduler", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile_name": self.profile_name,
            "postgres": self.postgres.to_dict(),
            "backup": self.backup.to_dict(),
            "logging": self.logging.to_dict(),
            "scheduler": self.scheduler.to_dict(),
        }


@dataclass(slots=True)
class AppSettings:
    schema_version: int = 1
    last_profile_path: str = ""
    recent_profile_paths: list[str] = field(default_factory=list)
    window_width: int = 980
    window_height: int = 720

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            last_profile_path=data.get("last_profile_path", ""),
            recent_profile_paths=[
                str(item).strip()
                for item in data.get("recent_profile_paths", [])
                if str(item).strip()
            ],
            window_width=int(data.get("window_width", 980)),
            window_height=int(data.get("window_height", 720)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)