# PG Backup Manager

Desktop-приложение для настройки, ручного запуска и регламентного выполнения резервного копирования PostgreSQL-баз 1С под Windows.

## Назначение проекта

PG Backup Manager создаётся как отдельное прикладное решение для:

- хранения профилей резервного копирования PostgreSQL;
- ручного запуска backup через графический интерфейс;
- запуска backup по расписанию через Планировщик задач Windows;
- ведения логов выполнения;
- дальнейшей сборки в Windows EXE.

## Основные цели

- уйти от разрозненных BAT/PS1-скриптов;
- предоставить единый интерфейс настройки backup;
- вынести бизнес-логику backup в отдельные слои проекта;
- подготовить проект к масштабированию и сопровождению.

## Архитектура проекта

Проект строится по слоям:

- `ui` — графический интерфейс;
- `app` — сценарии уровня приложения;
- `domain` — модели и правила предметной области;
- `infrastructure` — работа с PostgreSQL, логами, конфигами и Планировщиком задач;
- `shared` — общие утилиты, ошибки, пути.

## Структура репозитория

```text
pg-backup-manager/
├─ .github/
│  └─ workflows/
├─ docs/
│  ├─ architecture/
│  ├─ user-guide/
│  └─ dev-guide/
├─ resources/
│  ├─ icons/
│  └─ examples/
├─ scripts/
│  ├─ build/
│  └─ release/
├─ src/
│  └─ pg_backup_manager/
│     ├─ __init__.py
│     ├─ __main__.py
│     ├─ app/
│     ├─ domain/
│     ├─ infrastructure/
│     ├─ ui/
│     └─ shared/
├─ tests/
│  ├─ unit/
│  └─ integration/
├─ .gitignore
├─ .editorconfig
├─ README.md
├─ LICENSE
├─ pyproject.toml
├─ requirements-dev.txt
└─ CHANGELOG.md