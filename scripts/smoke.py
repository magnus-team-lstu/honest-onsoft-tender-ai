"""One real call to the ONSOFT model. Do not import this from tests."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

_SECRET = re.compile(r"sk-[A-Za-z0-9_\-]+")


def redact(text: str) -> str:
    return _SECRET.sub("sk-REDACTED", text)


def main() -> None:
    import asyncio

    asyncio.run(_once())


async def _once() -> None:
    load_dotenv()
    key = os.environ.get("ONSOFT_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        raise SystemExit("ONSOFT_API_KEY is not set")
    base_url = os.environ.get("LLM_BASE_URL", "https://ai.on-soft.ru/v1")
    model = os.environ.get("LLM_MODEL", "qwen3-6-practice")
    client = AsyncOpenAI(base_url=base_url, api_key=key, max_retries=0)
    started = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=64,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": 'Верни JSON {"ok": true}. Без пояснений.',
                }
            ],
        )
    except Exception as error:
        seconds = time.perf_counter() - started
        status = getattr(error, "status_code", None)
        _write(
            json_mode="ошибка",
            think="неизвестно",
            seconds=seconds,
            usage="нет",
            note=f"{type(error).__name__} status={status}: {redact(str(error))[:500]}",
        )
        print(f"smoke-error status={status} seconds={seconds:.1f}")
        return
    seconds = time.perf_counter() - started
    content = response.choices[0].message.content or ""
    usage = response.usage
    usage_text = "нет"
    if usage is not None:
        usage_text = (
            f"prompt={usage.prompt_tokens}, completion={usage.completion_tokens}"
        )
    _write(
        json_mode="да" if content.strip().startswith("{") else "текст не JSON",
        think="да" if "<think>" in content.lower() else "нет",
        seconds=seconds,
        usage=usage_text,
        note=f"finish={response.choices[0].finish_reason}, chars={len(content)}",
    )
    print(f"smoke-ok seconds={seconds:.1f} usage={usage_text}")


def _write(*, json_mode: str, think: str, seconds: float, usage: str, note: str) -> None:
    path = Path("docs/model-notes.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Заметки о модели ОНСОФТ",
                "",
                "Один запрос, 2026-11-08. Модель `qwen3-6-practice`, адрес `https://ai.on-soft.ru/v1`.",
                "",
                f"- `response_format=json_object`: {json_mode}",
                f"- блок `<think>`: {think}",
                f"- время: {seconds:.1f} с",
                f"- `usage`: {usage}",
                f"- подробность: {note}",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
