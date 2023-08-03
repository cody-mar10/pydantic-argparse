"""Arguments Utility Functions for Declarative Typed Argument Parsing.

The `arguments` module contains utility functions used for formatting argument
names and formatting argument descriptions.
"""

from typing import Optional, get_args

from .pydantic import PydanticField


def name(field: PydanticField, invert: bool = False) -> str:
    """Standardises argument name.

    Args:
        field (PydanticField): Field to construct name for.
        invert (bool): Whether to invert the name by prepending `--no-`.

    Returns:
        str: Standardised name of the argument.
    """
    # Construct Prefix
    prefix = "--no-" if invert else "--"
    name = field.info.title or field.name

    # Prepend prefix, replace '_' with '-'
    return f"{prefix}{name.replace('_', '-')}"


def description(field: PydanticField) -> str:
    """Standardises argument description.

    Args:
        field (PydanticField): Field to construct description for.

    Returns:
        str: Standardised description of the argument.
    """
    # Construct Default String
    default = (
        f"(default: {field.info.get_default()})"
        if not field.info.is_required()
        else None
    )

    # Return Standardised Description String
    return " ".join(filter(None, [field.info.description, default]))


def metavar(field: PydanticField) -> Optional[str]:
    """Generate the metavar name for the field.

    Args:
        field (PydanticField): Field to construct metavar for.

    Returns:
        Optional[str]: Field metavar if the `Field.info.alias` exists
    """
    # metavar is the type
    if field.info.annotation is not None:
        inner_types = get_args(field.info.annotation)
        if inner_types:
            return inner_types[0].__name__.upper()
        return field.info.annotation.__name__.upper()

    # this is pretty much unreachable
    if field.info.alias is not None:
        return field.info.alias.upper()

    return
