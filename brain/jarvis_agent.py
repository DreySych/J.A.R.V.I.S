import os
import sys
import json

import openai
from dotenv import load_dotenv

from jarvis_tools import load_modules, build_tools, execute_tool_call
from memory import MemoryManager
from memory_tool import MEMORY_TOOL, make_remember_fact
from prompt import build_instructions

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

load_dotenv()

YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_FOLDER_ID")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_AI_TOKEN")
YANDEX_CLOUD_MODEL = "deepseek-v4.1-flash"

if not YANDEX_CLOUD_FOLDER:
    raise RuntimeError("В .env не задан YANDEX_FOLDER_ID")

if not YANDEX_CLOUD_API_KEY:
    raise RuntimeError("В .env не задан YANDEX_AI_TOKEN")

_REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "modules_registry.json"
)

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER,
    timeout=60.0,
)

_memory = MemoryManager()
_remember_fact = make_remember_fact(_memory)

MEMORY_TOOL_NAME = "remember_fact"
MAX_MEMORY_CALLS = 3
MAX_TOOL_CALLS = 5

def register_memory_tool(all_tools):
    all_tools.append(MEMORY_TOOL)

def to_api_items(messages):
    items = []
    for m in messages:
        if m.get("type") == "tool":
            items.append({
                "role": "assistant",
                "content": f"[{m.get('name')}] {m.get('content')}",
            })
        elif m.get("role") in ("user", "assistant") and m.get("content"):
            items.append({"role": m["role"], "content": m["content"]})
    return items

def ask_jarvis(user_text):

    if not user_text or not user_text.strip():
        return "Сэр, сформулируйте запрос, пожалуйста."

    modules = load_modules(_REGISTRY_PATH)
    all_tools, tool_registry = build_tools(modules)
    register_memory_tool(all_tools)
    all_tools.insert(0, {
        "type": "web_search",
        "search_context_size": "low",
    })

    turn = _memory.add_user(user_text.strip())
    conversation = to_api_items(_memory.get_history())

    max_iterations = 5
    output_text = ""
    tool_calls_done = 0
    memory_calls = 0
    executed_signatures = set()

    for iteration in range(max_iterations):
        is_last = iteration == max_iterations - 1
        try:
            response = client.responses.create(
                model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
                temperature=0.3,
                instructions=build_instructions(_memory),
                input=conversation,
                max_output_tokens=1500,
                tools=None if is_last else all_tools,
            )
        except Exception as e:
            _memory.add_assistant("Сэр, произошла ошибка при обращении к модели.", turn)
            print("API error:", str(e))
            raise

        output_text = getattr(response, "output_text", "")

        if hasattr(response, "output") and response.output:
            calls = [
                item for item in (getattr(response, "output", None) or [])
                if getattr(item, "type", None) == "function_call"
            ]

            if calls:
                if output_text:
                    conversation.append({"role": "assistant", "content": output_text})

                for item in calls:
                    call_id = getattr(item, "call_id", "")
                    name = getattr(item, "name", "")
                    arguments_str = getattr(item, "arguments", "")
                    print(f"[iter {iteration}] call={name} args={arguments_str}")

                    try:
                        arguments_dict = json.loads(arguments_str or "{}")
                    except (json.JSONDecodeError, TypeError):
                        arguments_dict = {}

                    signature = (name, arguments_str)

                    if name == MEMORY_TOOL_NAME:
                        if memory_calls >= MAX_MEMORY_CALLS:
                            result = "Отклонено: слишком много фактов за один ответ."
                        else:
                            memory_calls += 1
                            try:
                                result = _remember_fact(**arguments_dict)
                            except TypeError as exc:
                                result = "Ошибка вызова remember_fact: {0}".format(exc)
                    elif signature in executed_signatures:
                        result = "Отклонено: этот вызов уже выполнялся в текущем запросе."
                    elif tool_calls_done >= MAX_TOOL_CALLS:
                        result = "Отклонено: слишком много вызовов инструментов за один ответ."
                    else:
                        executed_signatures.add(signature)
                        try:
                            result = execute_tool_call(name, arguments_dict, tool_registry)
                        except Exception as exc:
                            result = "Ошибка выполнения '{0}': {1}".format(name, exc)
                        tool_calls_done += 1 if not result.startswith("Ошибка") else 0

                    result = str(result)
                    print(f"[iter {iteration}] result={result[:200]!r}")

                    if not result.startswith("Отклонено"):
                        _memory.add_tool(name, result, turn)

                    conversation.append(item.model_dump(exclude_none=True))
                    conversation.append({
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": result,
                    })

                continue

        if not output_text:
            fallback = "Сэр, мне не удалось сформировать ответ. Попробуйте повторить запрос."
            _memory.add_assistant(fallback, turn)
            return fallback

        print(f"[iter {iteration}] types={[i.type for i in response.output or []]} text={output_text!r}")

        _memory.add_assistant(output_text, turn)

        print("Ответ J.A.R.V.I.S.:", output_text)
        return output_text

    if output_text:
        _memory.add_assistant(output_text, turn)
        return output_text

    fallback = "Сэр, не удалось завершить обработку запроса."
    _memory.add_assistant(fallback, turn)
    return fallback

if __name__ == "__main__":
    user_text = ("Узнай официальный курс доллара США к российскому рублю на сегодня по данным Банка России. "
                 "Назови курс, дату его действия и укажи, что это официальный курс ЦБ.")
    print(ask_jarvis(user_text))