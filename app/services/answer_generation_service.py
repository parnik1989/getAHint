from typing import Any, Dict, List


def generate_event_answer(query: str, results: List[Dict[str, Any]], upcoming_only: bool = True) -> str:
    if not results:
        return "I could not find matching upcoming events in the available data."

    category_groups = _category_groups(results)
    if len(category_groups) == 1:
        category_text = next(iter(category_groups))
        opening = f"I found these upcoming {category_text} events:"
    elif upcoming_only:
        opening = "I found these matching upcoming events:"
    else:
        opening = "I found these matching events:"

    lines = [opening]
    for event in results:
        category = event.get("category")
        category_suffix = f" [{category}]" if category else ""
        lines.append(
            f"- {event['event_name']} on {event['event_date']} at {event['event_address']}{category_suffix}. "
            f"{event['event_description']}"
        )
    return "\n".join(lines)


def _category_groups(results: List[Dict[str, Any]]) -> set[str]:
    return {str(result.get("category")) for result in results if result.get("category")}
