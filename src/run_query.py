import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import ValidationError, validate
from openai import OpenAI
from src.safety import evaluate_query_safety

PROMPTS_FILES = [Path("prompts/main_prompt.md"), Path("prompts/main_prompt.txt")]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"enum": ["ok", "needs_clarification", "refused", "error"]},
        "answer": {"type": "string"},
        "confidence": {"enum": ["low", "medium", "high"]},
        "actions": {"type": "array", "items": {"type": "string"}},
        "follow_up_question": {"type": ["string", "null"]},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["status", "answer", "confidence", "actions", "follow_up_question", "sources"],
    "additionalProperties": False,
}

def load_prompt() -> str:
    for prompt_file in PROMPTS_FILES:
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
    raise FileNotFoundError("No prompt file found in the expected locations.")


def estimate_cost_usd(tokens_prompt: int, tokens_completion: int) -> float:
    prompt_per_1k = float(os.getenv("OPENAI_COST_PROMPT_PER_1K_USD", "0"))
    completion_per_1k = float(os.getenv("OPENAI_COST_COMPLETION_PER_1K_USD", "0"))
    cost = ((tokens_prompt / 1000) * prompt_per_1k) + ((tokens_completion / 1000) * completion_per_1k)
    return round(cost, 8)


def save_output(data: dict) -> Path:
    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path = out_dir / filename
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def save_metrics_csv(metrics: dict) -> Path:
    metrics_dir = Path("metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)
    csv_path = metrics_dir / "metrics.csv"
    file_exists = csv_path.exists()

    with csv_path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "tokens_prompt",
                "tokens_completion",
                "total_tokens",
                "latency_ms",
                "estimated_cost_usd",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(metrics)

    return csv_path


def save_metrics_json(metrics: dict) -> Path:
    metrics_dir = Path("metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)
    json_path = metrics_dir / "metrics.json"

    if json_path.exists():
        existing = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(existing, list):
            existing = []
    else:
        existing = []

    existing.append(metrics)
    json_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return json_path


def build_metrics(*, prompt_tokens: int, completion_tokens: int, latency_ms: float) -> dict:
    total_tokens = prompt_tokens + completion_tokens
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tokens_prompt": prompt_tokens,
        "tokens_completion": completion_tokens,
        "total_tokens": total_tokens,
        "latency_ms": round(latency_ms, 2),
        "estimated_cost_usd": estimate_cost_usd(prompt_tokens, completion_tokens),
    }


def run_query(query: str) -> tuple[dict, dict]:
    load_dotenv()

    result = evaluate_query_safety(query) # Evalúa la seguridad de la consulta y obtiene el resultado
    blocked = result[0]
    fallback_response = result[1]
    matched_patterns = result[2]
    print(f"[SAFETY] blocked={blocked} matched_patterns={matched_patterns}")

    if blocked:
        response_data = fallback_response or {}
        validate(instance=response_data, schema=RESPONSE_SCHEMA)
        metrics = build_metrics(prompt_tokens=0, completion_tokens=0, latency_ms=0.0)
        return response_data, metrics

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    system_prompt = load_prompt()

    started = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "support_assistant_response",
                "strict": True,
                "schema": RESPONSE_SCHEMA,
            },
        },
        temperature=0.2,
        max_tokens=600,
    )
    latency_ms = (time.perf_counter() - started) * 1000

    content = response.choices[0].message.content or "{}"
    response_data = json.loads(content)
    validate(instance=response_data, schema=RESPONSE_SCHEMA)

    usage = response.usage
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    metrics = build_metrics(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
    )
    return response_data, metrics


def main() -> None:
    query = input("Ingresa la pregunta del cliente: ").strip()
    if not query:
        print("La pregunta no puede estar vacía.")
        return

    try:
        response_data, metrics = run_query(query)
        print("Respuesta JSON:")
        print(json.dumps(response_data, ensure_ascii=False, indent=2))

        output_path = save_output(response_data)
        metrics_csv_path = save_metrics_csv(metrics)
        metrics_json_path = save_metrics_json(metrics)

        print(f"Salida guardada en: {output_path}")
        print(f"Métricas guardadas en: {metrics_csv_path} y {metrics_json_path}")
    except json.JSONDecodeError as exc:
        print(f"La respuesta del modelo no fue JSON válido: {exc}")
    except ValidationError as exc:
        print(f"La respuesta no cumple el esquema esperado: {exc.message}")


if __name__ == "__main__":
    main()
