import json
import requests
import os
import logging

if os.getenv("JARVIS_DEBUG"):
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
    for name in ("urllib3", "httpcore", "httpcore2", "httpx", "httpx2", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)

_TYPE_MAP = {
    "int": "integer",
    "integer": "integer",
    "float": "number",
    "double": "number",
    "number": "number",
    "str": "string",
    "string": "string",
    "bool": "boolean",
    "boolean": "boolean",
}

def _convert_type(raw_type):
    return _TYPE_MAP.get(raw_type.lower(), "string")


def load_modules(path):
    if not path or not os.path.isfile(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, IOError):
        return []


def build_tools(modules):
    tools = []
    tool_registry = {}

    for module in modules:
        module_id = module.get("module_id", "")
        endpoint = module.get("endpoint", "")
        tool_defs = module.get("tools", [])

        safe_module_id = module_id.replace("-", "_")

        for tool_def in tool_defs:
            tool_name = tool_def.get("name", "")
            tool_description = tool_def.get("description", "")
            parameters_raw = tool_def.get("parameters", {})
            path = tool_def.get("path", "")
            optional = set(tool_def.get("optional", []))

            if not tool_name or not endpoint or not path:
                continue

            full_name = "{0}_{1}".format(safe_module_id, tool_name)

            properties = {}
            required = []

            for param_name, param_type in parameters_raw.items():
                properties[param_name] = {
                    "type": _convert_type(param_type),
                }
                if param_name not in optional:
                    required.append(param_name)

            schema = {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            }

            tools.append({
                "type": "function",
                "name": full_name,
                "description": tool_description,
                "parameters": schema,
            })

            tool_registry[full_name] = (module, tool_def)

    return tools, tool_registry


def execute_tool_call(tool_name, arguments_dict, tool_registry):
    if not tool_name:
        return "Ошибка: не указано имя инструмента."

    arguments_dict = arguments_dict or {}

    if tool_name not in tool_registry:
        return "Ошибка: инструмент '{0}' не найден.".format(tool_name)

    module, tool_def = tool_registry[tool_name]
    endpoint = module.get("endpoint", "")
    method = tool_def.get("method", "POST").upper()
    path = tool_def.get("path", "")
    parameters_schema = tool_def.get("parameters", {})
    optional = set(tool_def.get("optional", []))

    for param_name in parameters_schema:
        if param_name in optional:
            continue
        if param_name not in arguments_dict:
            return "Ошибка: отсутствует обязательный параметр '{0}'.".format(param_name)
        value = arguments_dict[param_name]
        if isinstance(value, str) and not value.strip():
            return "Ошибка: параметр '{0}' пуст. Укажите конкретное значение.".format(param_name)

    url = "{0}{1}".format(endpoint, path)

    body = {}
    for param_name, param_value in arguments_dict.items():
        if param_name in optional:
            if param_value is None or (isinstance(param_value, str) and not param_value.strip()):
                continue

        raw_type = parameters_schema.get(param_name, "string").lower()
        if raw_type in ("integer", "int"):
            try:
                body[param_name] = int(param_value)
            except (ValueError, TypeError):
                body[param_name] = param_value
        elif raw_type in ("number", "float", "double"):
            try:
                body[param_name] = float(param_value)
            except (ValueError, TypeError):
                body[param_name] = param_value
        elif raw_type in ("boolean", "bool"):
            if isinstance(param_value, str):
                body[param_name] = param_value.lower() in ("true", "1", "yes")
            else:
                body[param_name] = bool(param_value)
        else:
            body[param_name] = param_value

    timeout = float(tool_def.get("timeout", 15))

    try:
        use_query = bool(tool_def.get("query")) or method == "GET"

        kwargs = {"params": body} if use_query else {"json": body}
        response = requests.request(method, url, timeout=timeout, **kwargs)

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()

        if tool_def.get("binary") or content_type.startswith(("video/", "image/", "audio/", "application/octet-stream")):
            media_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
            os.makedirs(media_dir, exist_ok=True)

            ext = content_type.split("/")[-1] if "/" in content_type else ""
            if not ext or ext in ("octet-stream", "x-matroska"):
                ext = tool_def.get("ext", "bin")

            base_name = os.path.basename(str(arguments_dict.get("name") or tool_name))
            if base_name.lower().endswith("." + ext):
                filename = base_name
            else:
                filename = "{0}.{1}".format(base_name, ext)

            filepath = os.path.join(media_dir, filename)

            with open(filepath, "wb") as f:
                f.write(response.content)

            size_kb = len(response.content) / 1024.0

            if content_type.startswith("image/"):
                prefix = "Фото получено и сохранено"
            elif content_type.startswith("audio/"):
                prefix = "Аудио получено и сохранено"
            else:
                prefix = "Видео получено и сохранено"

            return "{0}: {1} ({2:.0f} КБ)".format(prefix, filepath, size_kb)

        if not response.text.strip():
            result_data = "Готово, модуль не вернул данных."
        else:
            try:
                result_data = response.json()
            except ValueError:
                result_data = response.text.strip()
    except requests.exceptions.Timeout:
        return "Ошибка: таймаут ({0} c) при вызове '{1}'. Команда могла выполниться.".format(
            int(timeout), tool_name
        )
    except requests.exceptions.ConnectionError:
        return "Ошибка: не удалось подключиться к модулю '{0}'.".format(
            module.get("module_id", "")
        )
    except requests.exceptions.HTTPError as exc:
        return "Ошибка HTTP при вызове '{0}': {1}.".format(tool_name, str(exc))

    if isinstance(result_data, dict):
        if "text" in result_data:
            return result_data["text"]
        else:
            return json.dumps(result_data, ensure_ascii=False)

    if isinstance(result_data, list):
        return json.dumps(result_data, ensure_ascii=False)

    return str(result_data)