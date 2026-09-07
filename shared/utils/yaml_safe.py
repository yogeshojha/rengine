"""Parse user-supplied YAML without letting aliases expand into a denial of service."""

from typing import Any

import yaml

# The largest document reNgine ships is a 24k-node nuclei template; this leaves headroom
# while stopping a payload whose aliases expand to tens of millions of nodes.
MAX_DOCUMENT_NODES = 100_000


class DocumentTooLargeError(ValueError):
    pass


def document_size(data: Any, *, limit: int = MAX_DOCUMENT_NODES) -> int:
    """Count nodes as a consumer walking the value would see them, stopping at the limit."""
    stack = [data]
    seen = 0
    while stack:
        node = stack.pop()
        seen += 1
        if seen > limit:
            msg = f"Document expands to more than {limit} values."
            raise DocumentTooLargeError(msg)
        if isinstance(node, dict):
            for key, value in node.items():
                stack.append(key)
                stack.append(value)
        elif isinstance(node, list | tuple):
            stack.extend(node)
    return seen


def load_document(text: str, *, limit: int = MAX_DOCUMENT_NODES) -> Any:
    """safe_load plus an expanded-size budget.

    PyYAML shares an aliased node rather than copying it, so parsing a billion-laughs
    payload is fast and small — the cost lands on whatever walks the result as a tree,
    which for us is pydantic. Measure the walk here, once, before handing it on.
    """
    data = yaml.safe_load(text)
    document_size(data, limit=limit)
    return data
