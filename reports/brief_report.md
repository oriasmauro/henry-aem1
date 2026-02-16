# Reporte - Customer Support Assistant

## 1) Arquitectura

El sistema se implementa como script ejecutable en `src/run_query.py`.

Flujo principal:
1. Recibe la pregunta del usuario por CLI.
2. Evalua fallback de seguridad local para entradas adversariales.
3. Si pasa seguridad, llama a `chat.completions` con:
   - `system prompt` desde `prompts/main_prompt.md`
   - `user prompt` con la pregunta
   - `response_format` con `json_schema` estricto
4. Valida el JSON de salida contra `RESPONSE_SCHEMA`.
5. Imprime y guarda respuesta en `outputs/`.
6. Registra metricas en `metrics/metrics.csv` y `metrics/metrics.json`.

Esta arquitectura prioriza un contrato estable de salida para integraciones downstream y observabilidad por consulta.

> Diagrama usando Mermaid
```mermaid
flowchart TD
    A[Usuario CLI<br/>Pregunta] --> B[run_query.py]
    B --> C{Safety Fallback<br/>Regex / Blocklist}
    C -- Detecta patrón adversarial --> D[Respuesta segura JSON<br/>+ escalate_to_human]
    C -- OK --> E[Cargar system prompt<br/>prompts/main_prompt.md]
    E --> F[Llamada OpenAI API<br/>chat.completions<br/>json_schema estricto]
    F --> G[Respuesta JSON del modelo]
    G --> H{Validación<br/>RESPONSE_SCHEMA}
    H -- Inválido --> I[Error / Manejo de excepción]
    H -- Válido --> J[Imprimir respuesta CLI]
    J --> K[Guardar en outputs/response_timestamp.json]
    J --> L[Registrar métricas<br/>metrics.csv + metrics.json]
    D --> L
  ```

## 2) Tecnica de Prompt Engineering elegida

Se eligio **few-shot prompting**.

Motivo:
- El objetivo principal es formato consistente y accionabilidad para agentes.
- Few-shot permite mostrar ejemplos de:
  - respuesta normal (`ok`)
  - falta de contexto (`needs_clarification`)
  - rechazo seguro (`refused`)
- En pruebas manuales, mejora consistencia del JSON y reduce desviaciones de estilo.

Trade-off:
- Aumenta tokens de prompt (mas costo/latencia).
- A cambio, reduce errores estructurales y simplifica consumo por UI/backends.

## 3) Metricas registradas

Por ejecucion se guardan:
- `tokens_prompt`
- `tokens_completion`
- `total_tokens`
- `latency_ms`
- `estimated_cost_usd`

`estimated_cost_usd` se calcula con tasas configurables en `.env`:
- `OPENAI_COST_PROMPT_PER_1K_USD`
- `OPENAI_COST_COMPLETION_PER_1K_USD`

Formula:
`(prompt_tokens/1000)*rate_prompt + (completion_tokens/1000)*rate_completion`

### Ejemplo de salida de metricas

```json
{
  "timestamp": "2026-02-15T20:00:00+00:00",
  "tokens_prompt": 520,
  "tokens_completion": 120,
  "total_tokens": 640,
  "latency_ms": 842.31,
  "estimated_cost_usd": 0.000294
}
```

## 4) Seguridad y robustez

Se incluye fallback local para patrones adversariales (prompt injection y terminos dañinos). Si se detecta riesgo:
- no se llama al modelo
- se devuelve JSON valido con `status="refused"`
- se registran metricas de ejecucion

Esto reduce exposicion a abuse cases en un entorno basico de soporte.

## 5) Testing automatizado

Se incluye `tests/test_core.py` con validaciones de:
- esquema JSON (caso valido e invalido)
- calculo de costo estimado
- armado de metricas
- deteccion adversarial basica

Esto cubre las partes criticas del contrato y observabilidad.
