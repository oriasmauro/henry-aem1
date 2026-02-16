import re

ADVERSARIAL_PATTERNS = [
    # Prompt injection / instruction override (EN + ES)
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"ignora(r)?\s+(todas?\s+)?(tus\s+)?instrucciones\s+(previas|anteriores)",
    r"reveal\s+(your\s+)?(system|hidden)\s+prompt",
    r"(revela|muestra)\s+(tu\s+)?(system\s+prompt|prompt\s+de\s+sistema)",
    r"olvida\s+las\s+instrucciones\s+anteriores",
    # Jailbreak / bypass (EN + ES)
    r"jailbreak",
    r"bypass\s+(security|safety)",
    r"(elude|omite|evita)\s+(la\s+)?(seguridad|moderaci[oó]n|filtros?)",
    # Harmful content keywords (EN + ES)
    r"hack(ear|eo|ing)?",
    r"hackeo|hackear|hacking",
    r"phishing",
    r"suplantaci[oó]n\s+de\s+identidad",
    r"malware",
    r"ransomware|spyware",
]


def safe_refusal_response() -> dict:
    return {
        "status": "refused",
        "answer": "No puedo ayudar con esa solicitud. Puedo ayudar con una respuesta segura orientada a soporte al cliente.",
        "confidence": "high",
        "actions": [
            "Solicitar una pregunta relacionada con soporte legítimo",
            "Escalar a revisión humana si se detecta abuso repetido",
        ],
        "follow_up_question": "¿Querés reformular tu consulta sobre un caso de soporte al cliente?",
        "sources": ["policy_guardrail_local"],
    }


def find_adversarial_matches(query: str) -> list[str]:
    matches: list[str] = []
    for pattern in ADVERSARIAL_PATTERNS:
        if re.search(pattern, query, flags=re.IGNORECASE):
            matches.append(pattern)
    return matches


def is_adversarial_query(query: str) -> bool:
    return len(find_adversarial_matches(query)) > 0


def evaluate_query_safety(query: str) -> tuple[bool, dict | None, list[str]]:
    matched_patterns = find_adversarial_matches(query)
    blocked = len(matched_patterns) > 0

    if blocked:
        return True, safe_refusal_response(), matched_patterns
    return False, None, matched_patterns
