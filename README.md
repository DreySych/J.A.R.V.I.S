# J.A.R.V.I.S.
Just A Really Very Intelligent System

### Самая свежая версия уже в ветке main!
Важно указать личные ключ и папку в env, иначе агент не будет работать

## Что уже сделано

- Настроено взаимодействие с Yandex AI Studio через OpenAI‑совместимый клиент (модель deepseek-v4-flash/latest)
- Реализован базовый агент J.A.R.V.I.S.:
  - файл: `brain/jarvis_agent.py`
  - функция: `ask_jarvis()`
- Подключён веб‑поиск
- Интеграция с Flask:
  - endpoint `POST /api/chat` принимает JSON `{"text": "..."}`
  - вызывает `ask_jarvis(...)` и получает текстовый ответ
  - текст передаётся в Silero TTS (модель для озвучки)
  - результат возвращается как WAV‑файл (`audio/wav`)