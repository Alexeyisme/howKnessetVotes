# howKnessetVotes

Публичный ресурс и REST API: как фракции и отдельные депутаты Кнессета голосовали по законопроектам. Поимённо, с историей фракций на дату голосования и ссылкой на официальный источник для каждой цифры.

Статус: этап 0 — аудит источников.

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
