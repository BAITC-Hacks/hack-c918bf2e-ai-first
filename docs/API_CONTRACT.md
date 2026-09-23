# MVP API contract

Контракт фиксирует границу параллельной разработки. Изменения согласуются между
backend и frontend до реализации.

## Создание анализа

`POST /api/v1/analyses` с `multipart/form-data`:

- `before_files`: один или несколько PDF/DOCX/XLSX;
- `after_files`: один или несколько PDF/DOCX/XLSX;
- `title`: необязательное название анализа.

Ответ `202 Accepted`:

```json
{
  "id": "analysis-uuid",
  "status": "queued",
  "created_at": "2026-09-23T13:30:00Z"
}
```

## Состояние и результат

`GET /api/v1/analyses/{id}`:

```json
{
  "id": "analysis-uuid",
  "title": "Реорганизация блока эксплуатации",
  "status": "completed",
  "progress": 100,
  "current_step": "Готово",
  "steps": [
    {"code": "extract", "title": "Извлечение документов", "status": "completed"},
    {"code": "structure", "title": "Выделение функций", "status": "completed"},
    {"code": "compare", "title": "Сопоставление", "status": "completed"},
    {"code": "verify", "title": "Проверка доказательств", "status": "completed"},
    {"code": "report", "title": "Формирование заключения", "status": "completed"}
  ],
  "summary": {
    "before_functions": 42,
    "after_functions": 44,
    "unchanged": 31,
    "lost": 3,
    "added": 5,
    "moved": 2,
    "changed": 4,
    "duplicates": 2,
    "high_risk": 3
  },
  "organization_changes": [
    {
      "id": "organization-change-uuid",
      "status": "created",
      "before_name": null,
      "after_name": "Департамент ИТ-аудита и анализа данных",
      "explanation": "В новой редакции создано специализированное подразделение.",
      "before": null,
      "after": {
        "department": "Блок внутреннего аудита",
        "clause": "3.4",
        "quote": "Департамент ИТ-аудита и анализа данных",
        "document": "Положение_редакция_9.docx",
        "page": null
      }
    }
  ],
  "quality_score": 0.91,
  "agent_trace": [
    {
      "agent": "orchestrator",
      "action": "plan",
      "status": "completed",
      "summary": "Выбрана стратегия полного сопоставления."
    },
    {
      "agent": "critic_agent",
      "action": "evaluate",
      "status": "completed",
      "summary": "Оценка качества: 91%."
    }
  ],
  "findings": [
    {
      "id": "finding-uuid",
      "type": "lost",
      "severity": "high",
      "title": "Утрата функции контроля аварийных работ",
      "explanation": "После реорганизации функция не закреплена ни за одним подразделением.",
      "confidence": 0.94,
      "before": {
        "department": "Департамент эксплуатации",
        "clause": "3.2.4",
        "quote": "Осуществляет контроль устранения аварий...",
        "document": "Положение_до.pdf",
        "page": 7
      },
      "after": null,
      "recommendation": "Назначить ответственное подразделение."
    }
  ],
  "conclusion": "Выявлены три отклонения высокого риска...",
  "warnings": []
}
```

`status`: `queued | processing | completed | failed`.

`finding.type`: `lost | added | moved | changed | duplicate | unchanged`.

`organization_changes.status`: `created | preserved | transformed | removed`.

`severity`: `high | medium | low | info`.

### Семантика источников и оценок

- `evidence.clause` может быть печатным номером (`3.4`), ссылкой `абзац 12`,
  `таблица 2, строка 3`, `Лист1!7` или `3.4 [фрагмент 2]` при повторении номера.
  Это строковый локатор; frontend не должен преобразовывать его в число.
- Для принятия доказательства обязательны точное имя документа, однозначный локатор
  и непрерывная цитата из фрагмента (различия в регистре и пробелах допускаются).
- `before_functions` / `after_functions` — модельная оценка, пока не полный реестр.
  `unchanged` — число явно сопоставленных пар с обеими цитатами, не остаток от вычитания
  числа отклонений. Ноль не означает, что все функции изменились.
- `quality_score` — оценка LLM-контролёра, не измеренная точность. Ошибки источников
  принудительно снижают её; замечания возвращаются в `warnings`.
- `conclusion` собирается из принятых находок и предупреждений; непроверенный
  свободный текст заключения модели в API не передаётся.

## Прогресс

Для MVP frontend опрашивает `GET /api/v1/analyses/{id}` каждые 1–2 секунды.
Если останется время, polling заменяется на SSE без изменения итоговой модели.

## Ошибка

```json
{
  "id": "analysis-uuid",
  "status": "failed",
  "progress": 35,
  "current_step": "Выделение функций",
  "steps": [],
  "error": {
    "code": "DOCUMENT_PARSE_ERROR",
    "message": "Не удалось извлечь текст из одного из документов."
  }
}
```
