"""AI Helper Module using Groq API for intelligent features."""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from config import GROQ_API_KEY, GROQ_MODEL, TIMEZONE

logger = logging.getLogger(__name__)


class GroqAI:
    """AI helper class for intelligent event parsing and suggestions."""

    def __init__(self, api_key: Optional[str] = None, model: str = GROQ_MODEL):
        self.api_key = api_key or GROQ_API_KEY
        self.model = model
        self.available = bool(self.api_key)

    async def parse_date_from_text(self, user_text: str) -> Optional[str]:
        """
        Parse natural language date from user input.
        Examples: "через неделю", "через 3 дня", "в следующий понедельник", "25.12.2024"

        Returns:
            Date string in YYYY-MM-DD format or None if parsing failed
        """
        if not self.available:
            return None

        system_prompt = """Ты парсер дат. Твоя задача - преобразовать текст пользователя в дату.
Ответь ТОЛЬКО датой в формате YYYY-MM-DD или словом "UNKNOWN" если не можешь распознать дату.

Поддерживаемые форматы:
- "через N дней/неделю/месяц" → дата через указанный период
- "завтра", "сегодня", "послезавтра"
- "в понедельник/вторник..." → ближайший такой день недели
- "25.12.2024", "2024-12-25", "25 декабря" → конкретная дата
- "день рождения", "Новый год", "Рождество" → соответствующие даты в текущем году

Если пользователь пишет дату - используй её. Если пишет "через неделю" - добавь 7 дней к сегодня."""

        user_prompt = f"Текущая дата: {datetime.now(TIMEZONE).strftime('%Y-%m-%d')}\nТекст пользователя: {user_text}"

        try:
            result = await self._call_api(system_prompt, user_prompt)
            if result and result != "UNKNOWN":
                # Validate date format
                datetime.strptime(result, "%Y-%m-%d")
                return result
        except Exception as e:
            logger.error(f"Date parsing error: {e}")

        return None

    async def parse_full_event_input(self, user_text: str) -> Optional[dict]:
        """
        Parse full natural language event input.
        Examples: "день рождения мамы через неделю", "встреча завтра", "Новый год 2025"

        Returns:
            Dict with 'name' and 'date' keys, or None if parsing failed
        """
        if not self.available:
            return None

        system_prompt = """Ты умный парсер событий. Пользователь вводит событие в свободной форме.
Твоя задача - извлечь название события и дату.

Ответь СТРОГО в формате JSON без markdown:
{"name": "название события", "date": "YYYY-MM-DD"}

Правила:
- Название: что именно за событие (день рождения, встреча, дедлайн и т.д.)
- Дата: конкретная дата в формате YYYY-MM-DD
- Поддерживаемые форматы дат в тексте:
  * "через N дней/неделю/месяц" → сегодня + N
  * "завтра", "сегодня", "послезавтра"
  * "в понедельник/вторник..." → ближайший такой день
  * "25.12.2024", "2024-12-25" → точная дата
  * "через неделю" = сегодня + 7 дней

Если не можешь распознать → верни {"name": null, "date": null}"""

        user_prompt = f"Текущая дата: {datetime.now(TIMEZONE).strftime('%Y-%m-%d')}\nВвод пользователя: {user_text}"

        try:
            result = await self._call_api(system_prompt, user_prompt)
            if result:
                # Parse JSON response
                import json as json_lib

                data = json_lib.loads(result)
                if data.get("name") and data.get("date"):
                    # Validate date
                    try:
                        datetime.strptime(data["date"], "%Y-%m-%d")
                        return {"name": data["name"].strip(), "date": data["date"]}
                    except ValueError:
                        pass
        except Exception as e:
            logger.error(f"Full event parse error: {e}")

        return None

    async def suggest_event_name(self, user_text: str) -> Optional[str]:
        """
        Suggest or improve event name from natural language.
        Examples: "день рождения мамы" → "День рождения мамы"

        Returns:
            Improved event name or None
        """
        if not self.available:
            return None

        system_prompt = """Ты помощник для создания названий событий.
Улучши название события, сделай его более информативным и красивым.
Ответь ТОЛЬКО улучшенным названием, без пояснений.

Правила:
- Первую букву - заглавную
- Используй кириллицу
- Будь кратким (3-10 слов)
- Если имя собственное - сохрани его"""

        try:
            result = await self._call_api(system_prompt, user_text)
            return result.strip() if result else None
        except Exception as e:
            logger.error(f"Event name suggestion error: {e}")

        return None

    async def categorize_event(self, event_name: str) -> str:
        """
        Categorize event based on its name.

        Categories:
        - birthday: дни рождения людей
        - holiday: праздники, праздничные даты
        - deadline: дедлайны, сроки, сдачи
        - meeting: встречи, переговоры
        - reminder: общие напоминания
        - anniversary: годовщины (свадьбы, знакомства и т.д.)
        - other: всё остальное

        Args:
            event_name: Name of the event to categorize

        Returns:
            Category string (one of: birthday, holiday, deadline, meeting, reminder, anniversary, other)
        """
        if not self.available:
            return "other"

        system_prompt = """Ты классификатор событий. Определи категорию события по его названию.

Категории:
- birthday: дни рождения людей ("день рождения", "др", " именины", "день рождения мамы")
- holiday: праздники ("новый год", "рождество", "8 марта", "пасха", "день победы", "выпускной")
- deadline: дедлайны, сроки ("сдать", "дедлайн", "крайний срок", "до")
- meeting: встречи ("встреча", "переговоры", "совещание", "конференция", "звонок")
- reminder: общие напоминания ("не забыть", "купить", "позвонить", "взять")
- anniversary: годовщины ("годовщина", "свадьбы", "знакомства", "вместе")
- other: всё остальное

Ответь ТОЛЬКО категорией на английском языке. Примеры:
"День рождения папы" → birthday
"Новый год 2025" → holiday
"Сдать отчёт" → deadline
"Встреча с клиентом" → meeting
"Купить продукты" → reminder
"Годовщина свадьбы" → anniversary
"Просто событие" → other"""

        try:
            result = await self._call_api(system_prompt, event_name)
            if result:
                category = result.strip().lower()
                # Validate category
                valid_categories = [
                    "birthday",
                    "holiday",
                    "deadline",
                    "meeting",
                    "reminder",
                    "anniversary",
                    "other",
                ]
                if category in valid_categories:
                    return category
        except Exception as e:
            logger.error(f"Event categorization error: {e}")

        return "other"

    async def generate_monthly_digest(
        self, events_by_category: dict, year: int, month: int
    ) -> str:
        """
        Generate monthly digest text from events grouped by category.

        Args:
            events_by_category: Dict with category as key, list of (date, name, local_id) as value
            year: Year
            month: Month number (1-12)

        Returns:
            Formatted digest text
        """
        import calendar

        month_name = calendar.month_name[month]

        if not events_by_category:
            return f"📅 *{month_name} {year}*\n\nУ тебя нет событий в этом месяце. 🎉"

        total_events = sum(len(events) for events in events_by_category.values())

        # Category emojis
        emoji_map = {
            "birthday": "🎂",
            "holiday": "🎉",
            "deadline": "⚠️",
            "meeting": "🤝",
            "reminder": "📌",
            "anniversary": "💍",
            "other": "📅",
        }

        # Ukrainian names for categories
        category_names = {
            "birthday": "дней рождения",
            "holiday": "праздников",
            "deadline": "дедлайнов",
            "meeting": "встреч",
            "reminder": "напоминаний",
            "anniversary": "годовщин",
            "other": "других событий",
        }

        # Build summary by category
        category_summary = []
        for category, events in sorted(events_by_category.items()):
            emoji = emoji_map.get(category, "📅")
            name = category_names.get(category, category)
            count = len(events)
            category_summary.append(f"{emoji} {count} {name}")

        # Format events list
        events_list = []
        for category, events in events_by_category.items():
            emoji = emoji_map.get(category, "📅")
            for date, name, local_id in events:
                # Format date
                try:
                    d = datetime.strptime(date.split()[0], "%Y-%m-%d")
                    date_str = d.strftime("%d.%m")
                except:
                    date_str = date
                events_list.append(f"  {emoji} #{local_id} {date_str} - {name}")

        digest = f"""📅 *{month_name} {year}*

📊 Всего событий: *{total_events}*

*По категориям:*
{chr(10).join(category_summary)}

*Список событий:*
{chr(10).join(events_list)}"""

        return digest

    async def smart_search(self, events: list, query: str, limit: int = 10) -> list:
        """
        Intelligent search using AI to understand context.

        Args:
            events: List of tuples (event_id, date, event_name)
            query: Search query in natural language

        Returns:
            Filtered list of events
        """
        if not self.available or not events:
            return events[:limit]

        # If query is simple, use fallback to fuzzy search
        if len(query) < 3 or query.isdigit():
            return events[:limit]

        event_list = "\n".join(
            [f"{i + 1}. {e[2]} (дата: {e[1]})" for i, e in enumerate(events)]
        )

        system_prompt = """Ты умный поисковик событий. Пользователь ищет события.
Найди ВСЕ события которые могут быть релевантны запросу.
Учитывай синонимы, похожие слова, контекст.

Ответь СПИСКОМ номеров (через запятую) найденных событий, в порядке убывания релевантности.
Например: "1, 3, 5, 8"
Если ничего не подходит - ответь "NONE\""""

        user_prompt = f"События:\n{event_list}\n\nЧто ищет пользователь: '{query}'"

        try:
            result = await self._call_api(system_prompt, user_prompt)
            if result and result != "NONE":
                # Parse result
                indices = []
                for part in re.findall(r"\d+", result):
                    idx = int(part) - 1
                    if 0 <= idx < len(events):
                        indices.append(idx)
                return [events[i] for i in indices if i < len(events)][:limit]
        except Exception as e:
            logger.error(f"Smart search error: {e}")

        return events[:limit]

    async def ai_search(self, all_events: list, query: str) -> list:
        """
        Полноценный AI-поиск по всем событиям.

        Args:
            all_events: Все события пользователя
            query: Поисковый запрос

        Returns:
            Отфильтрованный список событий
        """
        if not self.available or not all_events:
            return all_events

        # Для простых запросов используем fuzzy
        if len(query) < 3:
            return all_events

        # Формируем список событий для AI
        event_list = "\n".join(
            [f"{i + 1}. [{e[0]}] {e[2]} ({e[1]})" for i, e in enumerate(all_events)]
        )

        system_prompt = """Ты умный помощник для поиска событий.
Пользователь ищет: '{query}'
Найди ВСЕ события которые могут быть релевантны, учитывая:
- Синонимы ("др" = "день рождения", "др" = "другий")
- Частичные совпадения ("Жен" найдёт "Женя", "Жени", "Жене")
- Контекст ("поздравить" найдёт дни рождения)
- Похожие имена

Ответь ТОЛЬКО списком номеров через запятую.
Пример ответа: "1, 5, 12"
Если ничего не найдено: "NONE\""""

        user_prompt = f"Все события:\n{event_list}\n\nЗапрос: {query}"

        try:
            result = await self._call_api(system_prompt, user_prompt)
            if result and result.strip() != "NONE":
                indices = []
                for part in re.findall(r"\d+", result):
                    idx = int(part) - 1
                    if 0 <= idx < len(all_events):
                        indices.append(idx)
                return [all_events[i] for i in indices if i < len(all_events)]
        except Exception as e:
            logger.error(f"AI search error: {e}")

        return all_events

        # If query is simple, use fallback to fuzzy search
        if len(query) < 3 or query.isdigit():
            return events[:limit]

        event_names = "\n".join([f"{i + 1}. {e[2]}" for i, e in enumerate(events)])

        system_prompt = """Ты умный поисковик событий. Найди события которые наиболее релевантны запросу пользователя.
Ответь СПИСКОМ номеров (через запятую) наиболее подходящих событий, в порядке убывания релевантности.
Например: "1, 3, 5"
Если ничего не подходит - ответь "NONE\""""

        user_prompt = f"События:\n{event_names}\n\nЗапрос: {query}"

        try:
            result = await self._call_api(system_prompt, user_prompt)
            if result and result != "NONE":
                # Parse result
                indices = []
                for part in re.findall(r"\d+", result):
                    idx = int(part) - 1
                    if 0 <= idx < len(events):
                        indices.append(idx)

                return [events[i] for i in indices if i < len(events)][:limit]
        except Exception as e:
            logger.error(f"Smart search error: {e}")

        return events[:limit]

    async def generate_reminder_message(
        self, event_name: str, event_date: str, days_until: int, category: str = "other"
    ) -> str:
        """
        Generate category-aware reminder message.

        Args:
            event_name: Name of the event
            event_date: Date of the event in YYYY-MM-DD format
            days_until: Days until the event
            category: Event category (birthday, holiday, deadline, meeting, reminder, anniversary, other)

        Returns:
            Personalized reminder message based on category
        """
        # Category-specific prompts
        category_prompts = {
            "birthday": """Ты создаёшь напоминание о дне рождения.
Будь тёплым и дружелюбным.
Напомни что нужно поздравить человека!
Ответь ТОЛЬКО текстом (1 предложение).""",
            "holiday": """Ты создаёшь напоминание о празднике.
Будь весёлым и праздничным!
Ответь ТОЛЬКО текстом (1 предложение).""",
            "deadline": """Ты создаёшь напоминание о дедлайне.
Будь серьёзным и напомни о сроке!
Ответь ТОЛЬКО текстом (1 предложение).""",
            "meeting": """Ты создаёшь напоминание о встрече.
Будь деловым, напомни о времени и месте.
Ответь ТОЛЬКО текстом (1 предложение).""",
            "reminder": """Ты создаёшь напоминание.
Будь кратким, напомни что нужно сделать.
Ответь ТОЛЬКО текстом (1 предложение).""",
            "anniversary": """Ты создаёшь напоминание о годовщине.
Будь романтичным и тёплым!
Ответь ТОЛЬКО текстом (1 предложение).""",
            "other": """Ты создаёшь напоминание о событии.
Будь кратким и дружелюбным.
Ответь ТОЛЬКО текстом (1 предложение).""",
        }

        # Category emojis
        category_emoji = {
            "birthday": "🎂",
            "holiday": "🎉",
            "deadline": "⚠️",
            "meeting": "🤝",
            "reminder": "📌",
            "anniversary": "💍",
            "other": "📅",
        }

        if not self.available:
            # Fallback to simple message with emoji
            emoji = category_emoji.get(category, "📅")
            date_formatted = datetime.strptime(
                event_date.split()[0], "%Y-%m-%d"
            ).strftime("%d.%m.%Y")
            if days_until == 0:
                return f"{emoji} Сегодня: {event_name}"
            elif days_until == 1:
                return f"{emoji} Завтра: {event_name}"
            else:
                return f"{emoji} Через {days_until} дней: {event_name}"

        date_formatted = datetime.strptime(event_date.split()[0], "%Y-%m-%d").strftime(
            "%d.%m.%Y"
        )

        system_prompt = category_prompts.get(category, category_prompts["other"])

        # Add context
        user_prompt = (
            f"Событие: '{event_name}'\nДата: {date_formatted}\nЧерез {days_until} дней"
        )

        if days_until == 0:
            user_prompt = f"Событие '{event_name}' СЕГОДНЯ!"
        elif days_until == 1:
            user_prompt = f"Событие '{event_name}' ЗАВТРА!"

        try:
            result = await self._call_api(system_prompt, user_prompt)
            if result:
                emoji = category_emoji.get(category, "📅")
                return f"{emoji} {result.strip()}"
        except Exception as e:
            logger.error(f"Reminder message generation error: {e}")

        # Fallback
        emoji = category_emoji.get(category, "📅")
        return f"{emoji} {event_name} - через {days_until} дней"

    async def _call_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Make API call to Groq."""
        try:
            from groq import AsyncGroq

            client = AsyncGroq(api_key=self.api_key)

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=256,
                timeout=30,
            )

            return response.choices[0].message.content.strip()

        except ImportError:
            logger.warning("groq library not installed")
            return None
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None


# Global AI instance
ai = GroqAI()


# Fallback functions when AI is not available
async def parse_date_fallback(date_str: str) -> Optional[str]:
    """
    Fallback date parser without AI.
    Supports: YYYY-MM-DD, DD.MM.YYYY, DD/MM/YYYY
    """
    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]

    # Handle relative dates
    date_str_lower = date_str.lower().strip()
    today = datetime.now(TIMEZONE).date()

    if date_str_lower in ["сегодня", "today"]:
        return today.strftime("%Y-%m-%d")
    elif date_str_lower in ["завтра", "tomorrow"]:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_str_lower in ["послезавтра"]:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")

    # Try to extract number for "через N дней"
    match = re.search(r"через\s+(\d+)\s+дней?", date_str_lower)
    if match:
        days = int(match.group(1))
        return (today + timedelta(days=days)).strftime("%Y-%m-%d")

    match = re.search(r"через\s+(\d+)\s+недел", date_str_lower)
    if match:
        weeks = int(match.group(1))
        return (today + timedelta(weeks=weeks)).strftime("%Y-%m-%d")

    # Try parsing with formats
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt).date()
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None
