# howKnessetVotes

Публичный ресурс и REST API: как фракции и отдельные депутаты Кнессета голосовали по законопроектам. Поимённо, с историей фракций на дату голосования и ссылкой на официальный источник для каждой цифры.

Статус: этап 1 — вертикальный сценарий (загрузка → БД → API).

## Документы

- [docs/architecture.md](docs/architecture.md) — проектная спецификация v0.1 (целевая система)
- [docs/adr/0001-mvp-scope.md](docs/adr/0001-mvp-scope.md) — что из спецификации входит в MVP
- [docs/audit/source-audit.md](docs/audit/source-audit.md) — какие официальные данные есть и насколько они полны

## Аудит источников

Скрипты используют только стандартную библиотеку Python 3.12.

```sh
python3 audit/fetch_official.py          # официальные таблицы OData → audit/raw/official/
# дампы Open Knesset: https://production.oknesset.org/pipelines/data/knesset/<table>/<table>.csv → audit/raw/oknesset/
python3 audit/compare.py > docs/audit/compare-output.md
```

`audit/raw/` не коммитится.

## База данных

PostgreSQL 17 в Docker, схема MVP — [db/migrations/0001_core.sql](db/migrations/0001_core.sql).

```sh
docker compose -f infra/compose.yaml up -d --wait   # localhost:5433
uv run db/migrate.py                                 # применить миграции
uv run pytest                                        # тесты инвариантов схемы
```

## Загрузка данных

```sh
uv run hkv ingest --from 2025-01-01 --to 2025-06-30   # справочники + голосования периода из OData v4
uv run hkv ingest --from ... --to ... --skip-reference   # только голосования
uv run hkv verify --from 2025-01-01 --to 2025-06-30 --sample 30   # покрытие + выборочная сверка с источником

# история: периоды по 3 месяца раздаются N процессам; можно прервать и перезапустить — продолжит с места остановки
uv run hkv backfill --from 2016-09-27 --to 2026-09-27 --workers 5 --skip 2025-01-01..2025-06-30
tail -f logs/backfill.log     # строка на каждые ~10 голосований
uv run hkv status             # покрытие по годам + когда каждый процесс последний раз писал в лог

# старый Votes.svc (до 2021-07): официальные итоги, голосования, которых нет в v4, пометки «не вошло в итог»
uv run hkv legacy --from 2016-09-27 --to 2021-07-31   # лог: logs/legacy.log; запускать после v4 за тот же период, повтор безопасен
```

Сервер Кнессета отдаёт ~1 страницу (100 записей) за 2–2,5 с на процесс; 5 процессов работают без замедления и без ошибок WAF.

Сырые страницы источника сохраняются в `data/raw/` (не коммитится); каждая строка БД ссылается на свой `source_snapshot`. Проблемы данных не отбрасываются, а записываются в `data_issue`.

## Регулярное обновление

`uv run hkv update` — справочники (депутаты, фракции, должности) и перечитывание голосований за последние 30 дней (`--days`): новые голосования и исправления источника (прежние версии сохраняются в `row_revision`). В конце пишет `data_release` — его показывает `GET /api/v1/status`. Лог: `logs/update.log`, ~5 минут.

Ежедневно в 04:30 через launchd (macOS):

```sh
sed "s|REPO_DIR|$PWD|g" infra/launchd/il.hkv.update.plist > ~/Library/LaunchAgents/il.hkv.update.plist
launchctl load ~/Library/LaunchAgents/il.hkv.update.plist
```

Или cron: `30 4 * * * /path/to/repo/scripts/update.sh`.

## API

```sh
uv run uvicorn hkv.api.app:app --reload   # http://127.0.0.1:8000/docs — OpenAPI
```

| Endpoint | Что возвращает |
|---|---|
| `GET /api/v1/votes` | Голосования, новые сверху. Фильтры: `date_from`, `date_to` (дата голосования, Asia/Jerusalem, границы включены), `stage`, `motion_type`, `bill`, `faction`, `person`, `q`; повтор параметра = OR; `limit` ≤ 100, `cursor` |
| `GET /api/v1/votes/{id}` | Вопрос, поимённые счётчики, официальные итоги (до 2021-07), раскладка по фракциям на дату голосования |
| `GET /api/v1/votes/{id}/ballots` | Поимённый список: депутат, фракция тогда, выбор, статус участия |
| `GET /api/v1/members`, `/members/{id}` | Депутаты: мандаты, история фракций, участие в голосованиях и расхождения с большинством фракции (числитель, знаменатель) |
| `GET /api/v1/members/{id}/votes` | Голоса депутата; `deviated=true` — только против большинства своей фракции |
| `GET /api/v1/factions`, `/factions/{id}`, `/factions/{id}/votes` | Фракции созыва, состав во времени, единство; `split_only=true` — голосования с разделением |
| `GET /api/v1/bills`, `/bills/{id}` | Законопроекты, по которым голосовали: поиск, статус, инициаторы, все голосования |
| `GET /api/v1/terms`, `/status` | Созывы; дата и покрытие последнего обновления |

ID — официальные ID Кнессета; `source_url` ведёт на карточку голосования на сайте Кнессета.

## Веб-интерфейс

[apps/web](apps/web) — Next.js (App Router), серверный рендеринг поверх API: список голосований с фильтром стадии и страница голосования (вопрос, итоги, раскладка по фракциям на дату голосования, поимённая таблица, ссылка на источник).

```sh
cd apps/web && npm install && npm run dev   # http://localhost:3000, API ожидается на :8000 (HKV_API_URL)
```
