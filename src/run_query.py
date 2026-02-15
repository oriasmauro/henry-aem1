import json
import os
import csv
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from jsonschema import ValidationError, validate
from openai import OpenAI


PROMPTS_FILES = [Path("prompts/main_prompt.md"), Path("prompts/main_prompt.txt")]

def save_output(data: dict) -> Path:
    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path = out_dir / filename
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path

def load_prompts():
    for prompt_file in PROMPTS_FILES:
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
    raise FileNotFoundError("No prompt file found in the expected locations.")


def estimate_cost_usd(tokens_prompt: int, tokens_completion: int) -> float:
    # Configurable via .env to avoid hardcoding model prices.
    prompt_per_1k = float(os.getenv("OPENAI_COST_PROMPT_PER_1K_USD", "0"))
    completion_per_1k = float(os.getenv("OPENAI_COST_COMPLETION_PER_1K_USD", "0"))
    return round(((tokens_prompt / 1000) * prompt_per_1k) + ((tokens_completion / 1000) * completion_per_1k), 8)


def save_metrics_csv(metrics: dict) -> Path:
    metrics_dir = Path("metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)
    csv_path = metrics_dir / "metrics.csv"
    file_exists = csv_path.exists()

    with csv_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
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
        current = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(current, list):
            current = []
    else:
        current = []

    current.append(metrics)
    json_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return json_path


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"enum": ["ok", "needs_clarification", "refused", "error"]},
        "answer": {"type": "string"},
        "follow_up_question": {"type": ["string", "null"]},
        "sources": {
            "type": "array",
            "items": {"type": "string"}
        },
    },
    "required": ["status", "answer", "follow_up_question", "sources"],
    "additionalProperties": False,
}


def run_query(query: str) -> tuple[dict, dict]:
    load_dotenv()
    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    system_prompt = load_prompts()
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
                "name": "assistant_response",
                "strict": True,
                "schema": RESPONSE_SCHEMA,
            },
        },
        temperature=0.2,
        max_tokens=1000,
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    content = response.choices[0].message.content or ""
    data = json.loads(content)
    validate(instance=data, schema=RESPONSE_SCHEMA)

    usage = response.usage
    tokens_prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    tokens_completion = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", tokens_prompt + tokens_completion) or (tokens_prompt + tokens_completion))
    metrics = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "estimated_cost_usd": estimate_cost_usd(tokens_prompt, tokens_completion),
    }
    return data, metrics

if __name__ == "__main__":
    query = input("Ingresa tu pregunta: ")
    try:
        response, metrics = run_query(query)
        print("Response:")
        print(json.dumps(response, ensure_ascii=False, indent=2))
        saved_path = save_output(response)
        print(f"Guardado en: {saved_path}")
        metrics_csv_path = save_metrics_csv(metrics)
        metrics_json_path = save_metrics_json(metrics)
        print(f"Métricas guardadas en: {metrics_csv_path} y {metrics_json_path}")
    except json.JSONDecodeError as e:
        print(f"La respuesta no fue JSON válido: {e}")
    except ValidationError as e:
        print(f"La respuesta no cumple el esquema: {e.message}")
