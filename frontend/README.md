# Frontend — «Сверка» (AI First)

Vue 3 + Quasar + TypeScript SPA по дизайн-пакету «Сверка · AI First»
(`Дизайн-пакет Сверка AI First/handoff/HANDOFF.md`). Как адаптирован handoff под
API-контракт — в [`docs/DESIGN.md`](docs/DESIGN.md).

## Маршруты

| Маршрут | Экран |
|---|---|
| `/new` | Новый анализ: два комплекта, валидация DOCX/PDF/XLSX до 20 МБ, «Демо на тестовых данных» |
| `/analysis/:id/run` | Выполнение: 5 этапов, журнал агентов, прогресс, время, ошибка и повторный запуск |
| `/analysis/:id` | Обзор: сводка, журнал агентов и оценка критика, карта оргструктуры, таблица отклонений, QC-блок |
| `/analysis/:id?finding=<id>` | Панель отклонения: цитаты «до/после» с diff, объяснение, рекомендация |
| `/analysis/:id/conclusion` | Заключение: 5 секций, копирование, печать / PDF |

Статус анализа опрашивается каждые 1,5 с (`GET /api/v1/analyses/{id}`); после
`completed` экран выполнения через 500 мс переходит к результату.

## Запуск

```bash
npm install
npm run dev      # http://localhost:3001, backend — http://localhost:8010
npm run build    # vue-tsc + vite build
```

По умолчанию браузер обращается к `/api` на том же адресе, где открыт frontend.
В Docker nginx передаёт запросы в `backend:8010`; в dev/preview Vite — на
`http://localhost:8010`. Не нужно открывать порт backend в браузере или настраивать CORS.
nginx допускает до 200 МБ на весь запрос загрузки; backend отдельно ограничивает каждый
файл 20 МБ. Неизвестный API-маршрут возвращает ошибку API, а не HTML приложения.

Для внешнего backend можно задать `API_BASE` в `.env` Compose. При старте контейнера
`docker/40-app-config.sh` записывает его в `/config.js` (`window.__APP_CONFIG__.API_BASE`).
Если файл недоступен или значение пустое, используется локальный `/api` proxy;
демоданные вместо ошибки не подставляются. Внешний backend должен разрешать origin
frontend в CORS (`cors_origins`). `.front_env` автоматически Vite/Compose не читает.
Контейнер слушает порт 80, health check — `/healthz`.

## Демо-режим

«Демо на тестовых данных» заполняет оба комплекта заглушками (6 + 7) и открывает
локальный mock (`src/api/mock.ts`) с id `demo-…`: это демонстрация интерфейса на заранее
подготовленных данных (`src/api/fixtures/demo-analysis.json`), анализ документов не
выполняется. Маркировка видна на всех экранах, в заключении, копии и печати. Добавление
настоящего файла выводит форму из демо-режима.

## Тесты

```bash
npm test         # регрессии: demo/real, источники, охват, реестр, риски, заключение
```

## Структура

```text
src/
├── api/            types.ts (контракт), client.ts (fetch + таймауты), mock.ts, fixtures/
├── composables/    useAnalysis.ts (общий polling по id), analysisContext.ts
├── stores/         draft (файлы формы), theme (светлая/тёмная), reviewed (localStorage)
├── components/     AgentTrace, UploadZone, SummaryStrip, OrgMap, FindingsTable, FindingDrawer,
│                   EvidenceCard, RiskChip, TypeLabel, ConfidenceMeter
├── pages/          NewAnalysisPage, AnalysisShell, RunPage, OverviewPage, ConclusionPage
├── utils/          labels (словари, склонения), findings (сортировка, diff), conclusion, trace
└── css/            tokens.scss (--sv-* обе темы), app.scss, quasar.variables.scss
```
