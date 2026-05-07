from typing import Any, Dict, List


def generate_event_answer(query: str, results: List[Dict[str, Any]], upcoming_only: bool = True) -> str:
    if not results:
        return "I could not find any matching upcoming events in my knowledge. would you like to search anything else ?"

    category_groups = _category_groups(results)
    if len(category_groups) == 1:
        category_text = next(iter(category_groups))
        return f"I found {len(results)} upcoming {category_text} event{'s' if len(results) != 1 else ''}."
    elif upcoming_only:
        return f"I found {len(results)} matching upcoming event{'s' if len(results) != 1 else ''}."
    else:
        return f"I found {len(results)} matching event{'s' if len(results) != 1 else ''}."


def _category_groups(results: List[Dict[str, Any]]) -> set[str]:
    return {str(result.get("category")) for result in results if result.get("category")}
