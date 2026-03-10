from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pg_backup_manager.shared.paths import ensure_directory


@dataclass(slots=True)
class LogPaths:
    main_log_path: Path
    run_log_path: Path | None = None


class LoggingService:
    def __init__(self, log_dir: str | Path, main_log_name: str = "backup.log") -> None:
        self._log_dir = ensure_directory(log_dir)
        self._main_log_path = self._log_dir / main_log_name

    @property
    def main_log_path(self) -> Path:
        return self._main_log_path

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    def write_main_log(self, message: str, level: str = "INFO") -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} {level}: {message}\n"
        with self._main_log_path.open("a", encoding="utf-8") as file:
            file.write(line)

    def append_to_run_log(self, run_log_path: str | Path, message: str) -> None:
        path = Path(run_log_path)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} - {message}\n"
        with path.open("a", encoding="utf-8") as file:
            file.write(line)

    def write_process_output(self, run_log_path: str | Path, content: str) -> None:
        path = Path(run_log_path)
        with path.open("a", encoding="utf-8") as file:
            file.write(content)

    def get_log_paths(self, run_log_name: str | None = None) -> LogPaths:
        run_log_path = self._log_dir / run_log_name if run_log_name else None
        return LogPaths(main_log_path=self._main_log_path, run_log_path=run_log_path)