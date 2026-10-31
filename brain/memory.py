import json
import os
from datetime import datetime, timezone
from pathlib import Path

_MEMORY_FILE = Path(__file__).parent / "memory.json"
_MAX_TURNS = 8


class MemoryManager:
    def __init__(self, path: Path = _MEMORY_FILE, max_turns: int = _MAX_TURNS):
        self.path = Path(path)
        self.max_turns = max_turns
        self.messages: list[dict] = []
        self.facts: dict[str, str] = {}
        self._turn_seq = 0
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        messages = data.get("messages", [])
        if isinstance(messages, list):
            self.messages = [m for m in messages if isinstance(m, dict)]

        facts = data.get("facts", {})
        if isinstance(facts, dict):
            self.facts = {str(k): str(v) for k, v in facts.items()}

        self._turn_seq = max(
            (m.get("turn", 0) for m in self.messages),
            default=0,
        )

    def _save(self) -> None:
        payload = {
            "messages": self.messages,
            "facts": self.facts,
        }

        tmp = self.path.with_suffix(".tmp")

        try:
            tmp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, self.path)
        except OSError as exc:
            print(f"[memory] не удалось сохранить: {exc}")

    def add_user(self, text: str) -> int:
        self._turn_seq += 1
        self.messages.append({
            "role": "user",
            "content": text.strip(),
            "turn": self._turn_seq,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        self._trim()
        self._save()
        return self._turn_seq

    def add_assistant(self, text: str, turn: int) -> None:
        self.messages.append({
            "role": "assistant",
            "content": text.strip(),
            "turn": turn,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        self._trim()
        self._save()

    def add_tool(self, name: str, result: str, turn: int) -> None:
        self.messages.append({
            "type": "tool",
            "name": name,
            "content": str(result)[:500],
            "turn": turn,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        self._trim()
        self._save()

    def get_history(self) -> list[dict]:
        return [dict(m) for m in self.messages]

    def _trim(self) -> None:
        turns = sorted({m["turn"] for m in self.messages})

        if len(turns) <= self.max_turns:
            return

        keep = set(turns[-self.max_turns:])
        self.messages = [
            m for m in self.messages
            if m.get("turn") in keep
        ]

    def set_fact(self, key: str, value: str) -> None:
        self.facts[key] = str(value)
        self._save()

    def forget(self, key: str) -> None:
        if self.facts.pop(key, None) is not None:
            self._save()

    def facts_block(self) -> str:
        if not self.facts:
            return ""
        lines = [f"- {key}: {value}" for key, value in self.facts.items()]
        return "ИЗВЕСТНО О ПОЛЬЗОВАТЕЛЕ:\n" + "\n".join(lines)