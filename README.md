# PG Backup Manager

Desktop-приложение для настройки, ручного запуска и регламентного выполнения резервного копирования PostgreSQL-баз 1С под Windows.

## Что делает проект
- хранит профили резервного копирования;
- запускает backup через pg_dump / pg_dumpall;
- управляет задачами Планировщика Windows;
- ведёт логи выполнения;
- собирается в Windows EXE.

## Архитектура
- `ui` — интерфейс
- `app` — сценарии приложения
- `domain` — бизнес-сущности
- `infrastructure` — работа с PostgreSQL, JSON, логами и Планировщиком

## Запуск в dev
```powershell
.\.venv\Scripts\Activate.ps1
python -m pg_backup_manager