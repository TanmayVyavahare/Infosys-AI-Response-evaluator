"""Reference alignment for coverage/relevance estimates, never fact verification."""
import re

_STOP = set("a an the is are was were be been being of to from in on at as and or that this it its he she they does did do has have had with for which who what when how please".split())


def content_tokens(text: str) -> set[str]:
    words = re.findall(r"\w+", text.casefold())
    return {re.sub(r"(?:ing|ed|s)$", "", word) if len(word) > 5 else word
            for word in words if word not in _STOP}


def reference_coverage(reference: str, response: str) -> float:
    expected = content_tokens(reference)
    return len(expected & content_tokens(response)) / len(expected) if expected else 0.0
