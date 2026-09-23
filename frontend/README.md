# Frontend — AI First

Vue 3 + Quasar + TypeScript SPA для главного demo flow: загрузка комплектов
«до/после» → прогресс пяти шагов агента → KPI, таблица отклонений, панель
доказательств и итоговое заключение. Дизайн и wireframe: [`docs/DESIGN.md`](docs/DESIGN.md).
Контракт API: [`../docs/API_CONTRACT.md`](../docs/API_CONTRACT.md).

## Запуск

```bash
npm install
npm run dev      # http://localhost:3001, backend ожидается на http://localhost:8010
npm run build    # vue-tsc + vite build
```

Адрес backend берётся во время выполнения из `/config.js`
(`window.__APP_CONFIG__.API_BASE`). В Docker файл генерируется при старте
контейнера из переменной `API_BASE` (`docker/40-app-config.sh`), поэтому образ не
нужно пересобирать под другое окружение. Контейнер слушает порт 80, health check —
`/healthz`.

## Демо-режим

Кнопка «Демо-пример» (или «Продолжить на демо-данных» при недоступном backend)
создаёт анализ с id `demo-…`, который обслуживается локальным mock
(`src/api/mock.ts`) в точном формате контракта, включая поэтапный прогресс.
Такие анализы помечаются бейджем «Демо-данные».

## Структура

```text
src/
├── api/            types.ts (контракт), client.ts (fetch + таймауты), mock.ts
├── composables/    useAnalysisPolling.ts (опрос 1,5 с, до 3 повторов при сбоях)
├── components/     FileDropZone, RunProgress, KpiStrip, FindingsTable,
│                   FindingDetail, EvidenceCard, ConclusionPanel
├── pages/          UploadPage (/), AnalysisPage (/analyses/:id)
└── utils/labels.ts русские подписи, цвета типов и рисков
```
