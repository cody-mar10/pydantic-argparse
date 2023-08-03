"""Types Utility Functions for Declarative Typed Argument Parsing.

The `types` module contains a utility function used for determining and
comparing the types of `pydantic fields.
"""


import sys
from typing import Any, Tuple, Union

from .pydantic import PydanticField

# Version-Guarded
if sys.version_info < (3, 8):  # pragma: <3.8 cover
    from typing_extensions import get_origin
else:  # pragma: >=3.8 cover
    from typing import get_origin


def is_field_a(
    field: PydanticField,
    types: Union[Any, Tuple[Any, ...]],
) -> bool:
    """Checks whether the subject *is* any of the supplied types.

    The checks are performed as follows:

    1. `field` *is* one of the `types`
    2. `field` *is an instance* of one of the `types`
    3. `field` *is a subclass* of one of the `types`

    If any of these conditions are `True`, then the function returns `True`,
    else `False`.

    Args:
        field (PydanticField): Subject field to check type of.
        types (Union[Any, Tuple[Any, ...]]): Type(s) to compare field against.

    Returns:
        bool: Whether the field *is* considered one of the types.
    """
    # Create tuple if only one type was provided
    if not isinstance(types, tuple):
        types = (types,)

    # Get field type, or origin if applicable
    field_type = get_origin(field.info.annotation) or field.info.annotation

    # Check `isinstance` and `issubclass` validity
    # In order for `isinstance` and `issubclass` to be valid, all arguments
    # should be instances of `type`, otherwise `TypeError` *may* be raised.
    is_valid = all(isinstance(t, type) for t in (*types, field_type))

    # Perform checks and return
    return (
        field_type in types
        or (is_valid and isinstance(field_type, types))
        or (is_valid and issubclass(field_type, types))
    )
