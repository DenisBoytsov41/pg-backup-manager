from __future__ import annotations

import subprocess
from dataclasses import dataclass

from pg_backup_manager.domain.models import ScheduleType
from pg_backup_manager.shared.errors import SchedulerError


@dataclass(slots=True)
class ScheduledTaskInfo:
    exists: bool
    task_name: str
    raw_output: str = ""
    status: str | None = None
    next_run_time: str | None = None
    last_result: str | None = None
    task_to_run: str | None = None


class WindowsTaskScheduler:
    _WEEKDAY_ALIASES: dict[str, str] = {
        "MON": "MON",
        "MONDAY": "MON",
        "ПН": "MON",
        "ПОН": "MON",
        "ПОНЕДЕЛЬНИК": "MON",
        "TUE": "TUE",
        "TUESDAY": "TUE",
        "ВТ": "TUE",
        "ВТОРНИК": "TUE",
        "WED": "WED",
        "WEDNESDAY": "WED",
        "СР": "WED",
        "СРЕДА": "WED",
        "THU": "THU",
        "THURSDAY": "THU",
        "ЧТ": "THU",
        "ЧЕТВЕРГ": "THU",
        "FRI": "FRI",
        "FRIDAY": "FRI",
        "ПТ": "FRI",
        "ПЯТНИЦА": "FRI",
        "SAT": "SAT",
        "SATURDAY": "SAT",
        "СБ": "SAT",
        "СУББОТА": "SAT",
        "SUN": "SUN",
        "SUNDAY": "SUN",
        "ВС": "SUN",
        "ВОСКРЕСЕНЬЕ": "SUN",
    }

    def create_or_update_task(
        self,
        *,
        task_name: str,
        task_run_command: str,
        schedule_type: ScheduleType,
        start_time: str,
        days_of_week: list[str] | None = None,
        run_user: str = "",
        run_password: str | None = None,
        run_with_highest_privileges: bool = False,
    ) -> str:
        self.delete_task(task_name, ignore_missing=True)
        return self.create_task(
            task_name=task_name,
            task_run_command=task_run_command,
            schedule_type=schedule_type,
            start_time=start_time,
            days_of_week=days_of_week or [],
            run_user=run_user,
            run_password=run_password,
            run_with_highest_privileges=run_with_highest_privileges,
        )

    def create_task(
        self,
        *,
        task_name: str,
        task_run_command: str,
        schedule_type: ScheduleType,
        start_time: str,
        days_of_week: list[str] | None = None,
        run_user: str = "",
        run_password: str | None = None,
        run_with_highest_privileges: bool = False,
    ) -> str:
        if not task_name.strip():
            raise SchedulerError("Не указано имя задачи Планировщика.")

        if not task_run_command.strip():
            raise SchedulerError("Не указана команда запуска задачи.")

        if schedule_type == ScheduleType.DISABLED:
            raise SchedulerError("Нельзя создать задачу с типом расписания DISABLED.")

        args = [
            "schtasks",
            "/create",
            "/tn",
            task_name,
            "/tr",
            task_run_command,
            "/sc",
            schedule_type.value.upper(),
            "/st",
            start_time,
            "/f",
        ]

        if schedule_type == ScheduleType.WEEKLY:
            normalized_days = self._normalize_weekdays(days_of_week or [])
            if not normalized_days:
                raise SchedulerError("Для еженедельной задачи нужно указать хотя бы один день недели.")
            args.extend(["/d", ",".join(normalized_days)])

        if run_user.strip():
            args.extend(["/ru", run_user])

            normalized_run_user = run_user.strip().upper()
            is_system = normalized_run_user in {"SYSTEM", "NT AUTHORITY\\SYSTEM"}

            if not is_system:
                if run_password is None:
                    raise SchedulerError(
                        "Для указанного пользователя запуска нужно явно передать run_password "
                        "или использовать SYSTEM."
                    )

                if run_password:
                    args.extend(["/rp", run_password])
                else:
                    args.append("/np")

        if run_with_highest_privileges:
            args.extend(["/rl", "HIGHEST"])

        return self._run_schtasks(args)

    def delete_task(self, task_name: str, *, ignore_missing: bool = True) -> str:
        args = ["schtasks", "/delete", "/tn", task_name, "/f"]

        try:
            return self._run_schtasks(args)
        except SchedulerError as exc:
            if ignore_missing and self._looks_like_missing_task(str(exc)):
                return ""
            raise

    def run_task(self, task_name: str) -> str:
        args = ["schtasks", "/run", "/tn", task_name]
        return self._run_schtasks(args)

    def query_task(self, task_name: str) -> ScheduledTaskInfo:
        args = ["schtasks", "/query", "/tn", task_name, "/fo", "LIST", "/v"]
        completed = self._run_schtasks_process(args, check=False)

        stdout_text = self._decode_bytes(completed.stdout)
        stderr_text = self._decode_bytes(completed.stderr)
        combined = self._combine_output(stdout_text, stderr_text)

        if completed.returncode != 0:
            if self._looks_like_missing_task(combined):
                return ScheduledTaskInfo(
                    exists=False,
                    task_name=task_name,
                    raw_output=combined,
                )
            raise SchedulerError(combined.strip() or f"Ошибка запроса задачи '{task_name}'.")

        return self._parse_query_output(task_name=task_name, raw_output=combined)

    def task_exists(self, task_name: str) -> bool:
        info = self.query_task(task_name)
        return info.exists

    def _run_schtasks(self, args: list[str]) -> str:
        completed = self._run_schtasks_process(args, check=False)

        stdout_text = self._decode_bytes(completed.stdout)
        stderr_text = self._decode_bytes(completed.stderr)
        combined = self._combine_output(stdout_text, stderr_text)

        if completed.returncode != 0:
            raise SchedulerError(combined.strip() or "Ошибка выполнения schtasks.")

        return combined.strip()

    def _run_schtasks_process(self, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(args, capture_output=True, check=check)
        except FileNotFoundError as exc:
            raise SchedulerError("Не найден schtasks. Команда доступна только в Windows.") from exc
        except OSError as exc:
            raise SchedulerError(f"Не удалось выполнить schtasks: {exc}") from exc

    def _decode_bytes(self, data: bytes | None) -> str:
        if not data:
            return ""

        for encoding in ("cp866", "cp1251", "utf-8"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue

        return data.decode("utf-8", errors="replace")

    def _combine_output(self, stdout_text: str, stderr_text: str) -> str:
        parts: list[str] = []
        if stdout_text.strip():
            parts.append(stdout_text.strip())
        if stderr_text.strip():
            parts.append(stderr_text.strip())
        return "\n".join(parts)

    def _normalize_weekdays(self, days_of_week: list[str]) -> list[str]:
        result: list[str] = []

        for item in days_of_week:
            key = item.strip().upper()
            if not key:
                continue

            normalized = self._WEEKDAY_ALIASES.get(key)
            if not normalized:
                raise SchedulerError(f"Не удалось распознать день недели: {item}")

            if normalized not in result:
                result.append(normalized)

        return result

    def _looks_like_missing_task(self, text: str) -> bool:
        lowered = text.lower()
        return (
            "cannot find the file specified" in lowered
            or "не удается найти указанный файл" in lowered
            or "не удается найти указанный путь" in lowered
            or "the system cannot find the file specified" in lowered
            or "error:" in lowered and "cannot find" in lowered
        )

    def _parse_query_output(self, *, task_name: str, raw_output: str) -> ScheduledTaskInfo:
        fields: dict[str, str] = {}

        for line in raw_output.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()

        return ScheduledTaskInfo(
            exists=True,
            task_name=task_name,
            raw_output=raw_output,
            status=self._pick_field(fields, ["status", "состояние"]),
            next_run_time=self._pick_field(
                fields,
                ["next run time", "следующее время выполнения", "время следующего запуска"],
            ),
            last_result=self._pick_field(fields, ["last result", "последний результат"]),
            task_to_run=self._pick_field(fields, ["task to run", "задача для выполнения"]),
        )

    def _pick_field(self, fields: dict[str, str], keys: list[str]) -> str | None:
        for key in keys:
            if key in fields:
                return fields[key]
        return None