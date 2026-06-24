import re
import math
import json

# Whitelisted names only — nothing else is reachable from the eval'd expression
SAFE_NAMES = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "sqrt": math.sqrt, "exp": math.exp, "log": math.log,
    "abs": abs, "pi": math.pi, "e": math.e,
}

ALLOWED_PATTERN = re.compile(r"^[0-9x\.\+\-\*/\(\)\s,a-z]+$")


def safe_eval_expression(expression: str, x_value: float) -> float | None:
    """
    Evaluates a SINGLE-VARIABLE math expression at one x value, using only
    whitelisted function names and a regex gate against arbitrary syntax.
    Returns None if the expression is unsafe or fails to evaluate.
    """
    if not ALLOWED_PATTERN.match(expression.lower()):
        return None

    try:
        scope = dict(SAFE_NAMES)
        scope["x"] = x_value
        # __builtins__ explicitly removed — no import, no file access, no exec reachable
        result = eval(expression, {"__builtins__": {}}, scope)
        if isinstance(result, complex) or math.isnan(result) or math.isinf(result):
            return None
        return float(result)
    except Exception:
        return None


def render_function_plot(expression: str, x_min: float, x_max: float, num_points: int = 200) -> dict | None:
    """Computes (x, y) arrays for a function expression, ready for direct Plotly consumption."""
    xs = [x_min + (x_max - x_min) * i / (num_points - 1) for i in range(num_points)]
    ys = []
    for x in xs:
        y = safe_eval_expression(expression, x)
        ys.append(y)  # None values become gaps in the plotted line — Plotly handles this fine

    if all(y is None for y in ys):
        return None

    return {"x": xs, "y": ys}


def extract_plot_blocks(text: str) -> tuple[str, list[dict]]:
    """
    Finds ```plot {...}``` blocks in LLM-generated text, computes real point
    arrays for any function-type plots, and returns the cleaned text (with
    plot blocks replaced by a placeholder marker) plus a list of ready-to-render
    plot specs in order.
    """
    plots = []
    pattern = re.compile(r"```plot\s*([\s\S]*?)```")

    def replace(match):
        raw = match.group(1).strip()
        try:
            spec = json.loads(raw)
        except Exception:
            return ""  # drop unparseable blocks entirely rather than show broken JSON

        if spec.get("type") == "function":
            computed = render_function_plot(
                spec.get("expression", "x"),
                float(spec.get("x_min", -10)),
                float(spec.get("x_max", 10)),
            )
            if not computed:
                return ""
            plots.append({
                "type": "function",
                "x": computed["x"], "y": computed["y"],
                "title": spec.get("title", ""),
                "x_label": spec.get("x_label", "x"),
                "y_label": spec.get("y_label", "y"),
            })
        elif spec.get("type") == "scatter":
            series = spec.get("series", [])
            if not series:
                return ""
            plots.append({
                "type": "scatter", "series": series,
                "title": spec.get("title", ""),
                "x_label": spec.get("x_label", "x"),
                "y_label": spec.get("y_label", "y"),
            })
        else:
            return ""

        return f"\n[[PLOT_{len(plots) - 1}]]\n"

    cleaned_text = pattern.sub(replace, text)
    return cleaned_text, plots