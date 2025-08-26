# -*- coding: utf-8 -*-
import os, json, requests

class AIProviderError(Exception):
    pass

def _clean_json(s: str):
    import re
    m = re.search(r'\{.*\}', s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return json.loads(s)

def prompt_for_schema(text: str, schema_fields: list, locale_hint: str = "pt-BR") -> str:
    return f"""
Você é um assistente que extrai dados de relatórios de poços de petróleo.
Analise o TEXTO DO PDF abaixo e preencha APENAS o JSON com as chaves a seguir.

CHAVES OBRIGATÓRIAS (use string vazia "" quando não existir):
{schema_fields}

Regras:
- Retorne SOMENTE um objeto JSON válido (sem explicações).
- Preserve frações e unidades como aparecem (ex.: "2 7/8", "6.50 kg/m", "1350.31 m").
- Use ponto como separador decimal quando houver (ex.: 6.50).
- {locale_hint}

TEXTO DO PDF:
----------------
{text}
----------------
JSON:
""".strip()

def call_openai(text: str, schema_fields: list, model: str = None, api_key: str = None, base_url: str = None):
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIProviderError("OPENAI_API_KEY não definido no ambiente.")
    base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": model,
        "messages": [
            {"role":"system","content":"Você extrai campos de relatórios e devolve JSON puro."},
            {"role":"user","content": prompt_for_schema(text, schema_fields)}
        ],
        "temperature": 0.1
    }
    r = requests.post(url, headers=headers, json=data, timeout=60)
    if r.status_code >= 400:
        raise AIProviderError(f"OpenAI HTTP {r.status_code}: {r.text}")
    content = r.json()["choices"][0]["message"]["content"]
    return _clean_json(content)

def call_ollama(text: str, schema_fields: list, model: str = None, base_url: str = None):
    base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = model or os.getenv("OLLAMA_MODEL", "mistral")
    url = f"{base_url.rstrip('/')}/api/generate"
    prompt = prompt_for_schema(text, schema_fields)
    r = requests.post(url, json={"model": model, "prompt": prompt, "stream": False}, timeout=120)
    if r.status_code >= 400:
        raise AIProviderError(f"Ollama HTTP {r.status_code}: {r.text}")
    content = r.json().get("response","")
    return _clean_json(content)

PROVIDERS = {"openai": call_openai, "ollama": call_ollama}
