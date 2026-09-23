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

Состояние и результат сохраняются в PostgreSQL. Завершённый анализ доступен по тому же
ID после рестарта. Прерванные `queued/processing` переходят в `failed` с
`error.code = ANALYSIS_INTERRUPTED`: последний прогресс сохраняется, выполнявшийся
этап помечается `failed`. Автоматического продолжения нет; предложите новый запуск
с повторной загрузкой файлов. Форма JSON не изменилась. При недоступной БД API и
`GET /health` возвращают `503`, а не подменяют результат моками.

`finding.type`: `lost | added | moved | changed | duplicate | unchanged`.

`organization_changes.status`: `created | preserved | transformed | removed`.

`severity`: `high | medium | low | info`.

### Семантика источников и оценок

- `evidence.clause` может быть печатным номером (`3.4`), ссылкой `абзац 12`,
  `таблица 2, строка 3`, `Лист1!7` или `3.4 [фрагмент 2]` при повторении номера.
  Это строковый локатор; frontend не должен преобразовывать его в число.
- Для принятия доказательства обязательны точное имя документа, однозначный локатор
  и непрерывная цитата из фрагмента (различия в регистре и пробелах допускаются).
- `before_functions` / `after_functions` — количество записей в `function_registry.functions`
  соответствующей стороны, а не скалярная оценка LLM. `unchanged` — число записей реестра
  сопоставлений со статусом unchanged, не остаток от вычитания
  числа отклонений. Ноль не означает, что все функции изменились.
- `quality_score` — оценка LLM-контролёра после кодовых ограничений, не измеренная
  точность. При замечаниях детерминированной проверки, включая незакрытые
  сопоставления, итог не выше 0,49; исходный балл модели отдельно не сохраняется.
  Замечания возвращаются в `warnings`.
- `conclusion` собирается из принятых находок и предупреждений; непроверенный
  свободный текст заключения модели в API не передаётся.

## Реестр функций (добавочное поле)

`function_registry` может отсутствовать в старых результатах/mock или быть `null` до
завершения. Старые поля сохранены. Пример с одной функцией без закрытого сопоставления:

```json
{
  "function_registry": {
    "functions": [{
      "id": "B0001-F01", "source_id": "B0001", "side": "before",
      "action": "Контроль сроков закупок", "owner": "Отдел контроля",
      "evidence": {"document": "before.docx", "clause": "1.3",
        "quote": "Отдел контроля проверяет соблюдение сроков закупок.",
        "department": "Отдел контроля", "page": null}
    }],
    "source_reviews": [{
      "source_id": "B0001", "side": "before", "document": "before.docx",
      "clause": "1.3", "status": "functions", "reason": "Явная обязанность"
    }],
    "mappings": [{
      "before_id": "B0001-F01", "after_ids": [], "status": "needs_review",
      "explanation": "Модель не вернула однозначное сопоставление функции."
    }],
    "coverage": {
      "total_fragments": 1, "reviewed_fragments": 1, "unresolved_fragments": 0,
      "before_functions": 1, "after_functions": 0,
      "matched_before_functions": 0, "needs_review_mappings": 1
    }
  }
}
```

- `source_reviews.status`: `functions | non_functional | needs_review`.
  Каждый извлечённый парсером фрагмент обязательно представлен, даже при ошибке API.
- `mappings.status`: `unchanged | moved | changed | lost | added | needs_review`.
  На каждую функцию ДО — одна строка. `after_ids` допускает несколько функций;
  несопоставленные функции ПОСЛЕ получают строку с `before_id: null`.
  У `needs_review` список `after_ids` может содержать кандидатов обратной сверки:
  это источники для проверки, а не подтверждённая эквивалентность. Прежние связи
  сохраняются, противоречие с предполагаемой потерей объясняется в `explanation`.
- Сопоставление выполняется отдельными пакетами; исправление аналитического отчёта
  сохраняет реестр, а не переписывает сотни связей повторно.
- Отсутствующая/повторная запись модели, неизвестный ID или противоречие не закрывает
  сопоставление. При неполном извлечении противоположного комплекта lost/added
  в реестре понижается до needs_review.
- `matched_before_functions` считает только unchanged/moved/changed, не lost.
  Метрики отражают обработку и состояние сопоставлений, а не фактическую точность.
- ID устойчивы при повторной обработке того же порядка документов и фрагментов;
  не предназначены для идентификации функции между разными анализами.

## Структурные риски (добавочное поле)

`structural_risks` — отдельный список потенциальных рисков внутри одной редакции.
`kind`: `duplicate | conflict_interest`. Каждый объект содержит `id`, `kind`,
`severity`, `title`, `explanation`, `confidence`, `recommendation` и
`evidence: [{side: "before" | "after", evidence: Evidence}, ...]`.
Для принятия нужны 2–6 проверяемых цитат, как минимум два разных локатора одного
комплекта. Это позволяет корректно представить две ссылки ПОСЛЕ, не переименовывая
старое поле `finding.before`. Риски между разными редакциями отклоняются.

`null` или отсутствие поля означает, что этот блок не передан/не выполнялся в старой
версии. `[]` означает отсутствие принятых находок, не доказанное отсутствие рисков.
`summary` по-прежнему считает `findings`, а не отдельные `structural_risks`.
Новые duplicate идут в этот блок; legacy FindingType сохранён для старых данных,
но новые пары ДО/ПОСЛЕ с type=duplicate не принимаются как доказательство дублирования.
Потенциальный конфликт интересов не равен дублированию и требует отдельной проверки.

Полный пример и задача на интерфейс: [FRONTEND_RISKS_HANDOFF.md](FRONTEND_RISKS_HANDOFF.md).

## Прогресс

Для MVP frontend опрашивает `GET /api/v1/analyses/{id}` каждые 1–2 секунды.
Переходы этапов приходят из фактического pipeline; проценты обозначают этап, не ETA.
`agent_trace` пополняется после завершения реальных операций, ещё до готовности отчёта.
`function_registry` может появиться при `processing` после извлечения; до окончания
сопоставления его `mappings` не завершены. Оба поля сохраняются в БД и остаются
доступными при последующей ошибке. Наличие промежуточного реестра не означает `completed`.
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
