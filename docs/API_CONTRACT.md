# MVP API contract

Контракт фиксирует границу параллельной разработки. Изменения согласуются между
backend и frontend до реализации.

## Создание анализа

`POST /api/v1/analyses` с `multipart/form-data`:

- `before_files`: один или несколько PDF/DOCX;
- `after_files`: один или несколько PDF/DOCX;
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

`severity`: `high | medium | low | info`.

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
