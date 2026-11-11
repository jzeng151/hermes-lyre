"""The ``transform_llm_output`` callback.

Returning ``None`` leaves the reply unchanged. Lyre is opt-in, so until the rewrite
(and the ``/a11y`` switch) is wired up the hook never changes anything.
"""

from __future__ import annotations

from typing import Any


def transform_llm_output(response_text: str = "", platform: str = "", **kwargs: Any) -> str | None:
    return None
