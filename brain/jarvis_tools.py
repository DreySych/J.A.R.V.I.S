import json
import os
import requests

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
        description = module.get("description", "")
        tool_defs = module.get("tools", [])

        safe_module_id = module_id.replace("-", "_")

        for tool_def in tool_defs:
            tool_name = tool_def.get("name", "")
            tool_description = tool_def.get("description", "")
            parameters_raw = tool_def.get("parameters", {})
            method = tool_def.get("method", "POST")
            path = tool_def.get("path", "")

            if not tool_name or not endpoint or not path:
                continue

            full_name = "{0}_{1}".format(safe_module_id, tool_name)

            properties = {}
            required = []

            for param_name, param_type in parameters_raw.items():
                properties[param_name] = {
                    "type": _convert_type(param_type),
                }
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
    if not tool_name or not arguments_dict:
        return "Ошибка: неверные аргументы инструмента."

    if tool_name not in tool_registry:
        return "Ошибка: инструмент '{0}' не найден.".format(tool_name)

    module, tool_def = tool_registry[tool_name]
    endpoint = module.get("endpoint", "")
    method = tool_def.get("method", "POST").upper()
    path = tool_def.get("path", "")
    parameters_schema = tool_def.get("parameters", {})

    for param_name in parameters_schema:
        if param_name not in arguments_dict:
            return "Ошибка: отсутствует обязательный параметр '{0}' для инструмента '{1}'.".format(
                param_name,
                tool_name,
            )

    url = "{0}{1}".format(endpoint, path)

    body = {}
    for param_name, param_value in arguments_dict.items():
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

    try:
        if method == "GET":
            response = requests.get(url, json=body, timeout=10.0)
        elif method == "PUT":
            response = requests.put(url, json=body, timeout=10.0)
        elif method == "DELETE":
            response = requests.delete(url, json=body, timeout=10.0)
        else:
            response = requests.post(url, json=body, timeout=10.0)

        response.raise_for_status()
        result_data = response.json()
    except requests.exceptions.Timeout:
        return "Ошибка: таймаут при вызове инструмента '{0}'.".format(tool_name)
    except requests.exceptions.ConnectionError:
        return "Ошибка: не удалось подключиться к модулю '{0}'.".format(
            module.get("module_id", ""),
        )
    except requests.exceptions.HTTPError as exc:
        return "Ошибка HTTP при вызове '{0}': {1}.".format(tool_name, str(exc))
    except (json.JSONDecodeError, ValueError):
        return "Ошибка: модуль вернул некорректный ответ."

    if isinstance(result_data, dict):
        if "text" in result_data:
            return result_data["text"]
        else:
            return json.dumps(result_data, ensure_ascii=False)

    if isinstance(result_data, list):
        return json.dumps(result_data, ensure_ascii=False)

    return str(result_data)
