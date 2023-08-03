"""Parses Nested Pydantic Model Fields to Sub-Commands.

The `command` module contains the `should_parse` function, which checks whether
this module should be used to parse the field, as well as the `parse_field`
function, which parses nested `pydantic` model fields to `ArgumentParser`
sub-commands.
"""

import argparse
from typing import Optional, Type, cast

from pydantic import BaseModel

from pydantic_argparse import utils
from pydantic_argparse.utils.pydantic import (
    PydanticField,
    PydanticValidator,
    is_subcommand,
)


def should_parse(field: PydanticField) -> bool:
    """Checks whether the field should be parsed as a `command`.

    Args:
        field (PydanticField): Field to check.

    Returns:
        bool: Whether the field should be parsed as a `command`.
    """
    # Check and Return
    if utils.types.is_field_a(field, BaseModel):
        model_type = cast(Type[BaseModel], field.info.annotation)
        return is_subcommand(model_type)
    return False


def parse_field(
    subparser: argparse._SubParsersAction,
    field: PydanticField,
) -> Optional[PydanticValidator]:
    """Adds command pydantic field to argument parser.

    Args:
        subparser (argparse._SubParsersAction): Sub-parser to add to.
        field (PydanticField): Field to be added to parser.

    Returns:
        Optional[PydanticValidator]: Possible validator method.
    """
    # Add Command
    subparser.add_parser(
        field.info.title or field.info.alias or field.name,
        help=field.info.description,
        model=field.info.annotation,  # type: ignore[call-arg]
        exit_on_error=False,  # Allow top level parser to handle exiting
    )

    # Return
    return None
