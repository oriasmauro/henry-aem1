# Multitasking Text Utility (Customer Support Assistant)

Aplicacion minima que recibe una pregunta de soporte, llama a OpenAI y devuelve JSON estructurado para sistemas downstream.

## Contrato de salida JSON

El asistente devuelve y valida este esquema:

```json
{
  "status": "ok | needs_clarification | refused | error",
  "answer": "string",
  "confidence": "low | medium | high",
  "actions": ["string"],
  "follow_up_question": "string | null",
  "sources": ["string"]
}
```

## Requisitos

- Python 3.11+
- `uv`

## Setup

```bash
cp .env.example .env
# completar OPENAI_API_KEY y opcionalmente OPENAI_MODEL / costos
uv sync --group dev
```

## Ejecutar

```bash
uv run python src/run_query.py
```

El script:
- imprime la respuesta JSON en consola
- guarda respuesta en `outputs/response_YYYYMMDD_HHMMSS.json`
- registra metricas en `metrics/metrics.csv` y `metrics/metrics.json`

## Metricas registradas por ejecucion

- `timestamp`
- `tokens_prompt`
- `tokens_completion`
- `total_tokens`
- `latency_ms`
- `estimated_cost_usd`

## Prompt engineering aplicado

Se usa **few-shot prompting** en `prompts/main_prompt.md` para estabilizar:
- formato JSON
- tono conciso de soporte
- manejo de casos ambiguos y rechazo seguro

## Seguridad (bonus)

Incluye fallback local de seguridad para inputs adversariales (ej. prompt injection o solicitudes dañinas). Cuando se activa, devuelve JSON con `status="refused"` sin llamar al modelo.

## Tests

```bash
uv run pytest -q
```
