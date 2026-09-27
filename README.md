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
```

Сырые страницы источника сохраняются в `data/raw/` (не коммитится); каждая строка БД ссылается на свой `source_snapshot`. Проблемы данных не отбрасываются, а записываются в `data_issue`.

## API

```sh
uv run uvicorn hkv.api.app:app --reload   # http://127.0.0.1:8000/docs — OpenAPI
```

| Endpoint | Что возвращает |
|---|---|
| `GET /api/v1/votes` | Голосования, новые сверху. Фильтры: `date_from`, `date_to` (дата голосования, Asia/Jerusalem, границы включены), `stage`, `motion_type`, `bill`, `faction`, `person`, `q`; повтор параметра = OR; `limit` ≤ 100, `cursor` |
| `GET /api/v1/votes/{id}` | Вопрос, поимённые счётчики, официальные итоги (до 2021-07), раскладка по фракциям на дату голосования |
| `GET /api/v1/votes/{id}/ballots` | Поимённый список: депутат, фракция тогда, выбор, статус участия |

ID — официальные ID Кнессета; `source_url` ведёт на карточку голосования на сайте Кнессета.
