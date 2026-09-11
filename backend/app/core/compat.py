"""Compatibility patch for Python 3.14 RC + pydantic.

Python 3.14.0rc2 removed the `prefer_fwd_module` keyword argument from
`typing._eval_type`, but current pydantic releases still pass it.
This module wraps the function to accept and ignore that keyword so
FastAPI and pydantic can load without errors.

This patch should be removed once pydantic ships a release that is fully
compatible with the final Python 3.14.
"""

import sys
import typing

_original_eval_type = typing._eval_type


def _patched_eval_type(*args, **kwargs):
    kwargs.pop("prefer_fwd_module", None)
    return _original_eval_type(*args, **kwargs)


if sys.version_info >= (3, 14):
    typing._eval_type = _patched_eval_type
