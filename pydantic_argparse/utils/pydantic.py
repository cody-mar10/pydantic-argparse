"""Pydantic Utility Functions for Declarative Typed Argument Parsing.

The `pydantic` module contains utility functions used for interacting with the
internals of `pydantic`, such as constructing field validators, updating
field validator dictionaries and constructing new model classes with
dynamically generated validators and environment variable parsers.
"""

from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    NamedTuple,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

import pydantic
from pydantic import BaseModel
from pydantic.fields import FieldInfo

# Constants
T = TypeVar("T")
PydanticModelT = TypeVar("PydanticModelT", bound=BaseModel)
PydanticValidator = classmethod


class PydanticField(NamedTuple):
    """Simple Pydantic v2.0 field wrapper.

    Pydantic fields no longer store their name, so this named tuple
    keeps the field name and field info together.
    """

    name: str
    info: FieldInfo

    @classmethod
    def parse_model(
        cls, model: BaseModel | Type[BaseModel]
    ) -> Iterator["PydanticField"]:
        """Iterator over the pydantic model fields, yielding this wrapper class.

        Yields:
            `PydanticField`
        """
        for name, info in model.model_fields.items():
            yield cls(name, info)


def as_validator(
    field: PydanticField,
    caster: Callable[[str], Any],
) -> PydanticValidator:
    """Shortcut to wrap a caster and construct a validator for a given field.

    The provided caster function must cast from a string to the type required
    by the field. Once wrapped, the constructed validator will pass through any
    non-string values, or any values that cause the caster function to raise an
    exception to let the built-in `pydantic` field validation handle them. The
    validator will also cast empty strings to `None`.

    Args:
        name (str): field name
        field (pydantic.fields.FieldInfo): Field to construct validator for.
        caster (Callable[[str], Any]): String to field type caster function.

    Returns:
        PydanticValidator: Constructed field validator function.
    """

    # Dynamically construct a `pydantic` validator function for the supplied
    # field. The constructed validator must be `pre=True` so that the validator
    # is called before the built-in `pydantic` field validation occurs and is
    # provided with the raw input data. The constructed validator must also be
    # `allow_reuse=True` so the `__validator` function name can be reused
    # multiple times when being decorated as a `pydantic` validator. Note that
    # despite the `__validator` function *name* being reused, each instance of
    # the validator function is uniquely constructed for the supplied field.
    @pydantic.validator(field.name, pre=True, allow_reuse=True)
    def __validator(cls: Type[Any], value: T) -> Optional[Union[T, Any]]:
        if not isinstance(value, str):
            return value
        if not value:
            return None
        try:
            return caster(value)
        except Exception:
            return value

    # Rename the validator uniquely for this field to avoid any collisions. The
    # leading `__` and prefix of `pydantic_argparse` should guard against any
    # potential collisions with user defined validators.
    __validator.__name__ = f"__pydantic_argparse_{field.name}"  # type: ignore

    # Return the constructed validator
    return __validator  # type: ignore


def update_validators(
    validators: Dict[str, PydanticValidator],
    validator: Optional[PydanticValidator],
) -> None:
    """Updates a validators dictionary with a possible new field validator.

    Note that this function mutates the validators dictionary *in-place*, and
    does not return the dictionary.

    Args:
        validators (Dict[str, PydanticValidator]): Validators to update.
        validator (Optional[PydanticValidator]): Possible field validator.
    """
    # Check for Validator
    if validator:
        # Add Validator
        validators[validator.__name__] = validator


def model_with_validators(
    model: Type[PydanticModelT],
    validators: Dict[str, PydanticValidator],
) -> Type[PydanticModelT]:
    """Generates a new `pydantic` model class with the supplied validators.

    If the supplied base model is a subclass of `pydantic.BaseSettings`, then
    the newly generated model will also have a new `parse_env_var` classmethod
    monkeypatched onto it that suppresses any exceptions raised when initially
    parsing the environment variables. This allows the raw values to still be
    passed through to the `pydantic` field validators if initial parsing fails.

    Args:
        model (Type[PydanticModelT]): Model type to use as base class.
        validators (Dict[str, PydanticValidator]): Field validators to add.

    Returns:
        Type[PydanticModelT]: New `pydantic` model type with field validators.
    """
    # Construct New Model with Validators
    model = pydantic.create_model(
        model.__name__,
        __base__=model,
        __validators__=validators,
    )

    # Check if the model is a `BaseSettings`
    # if issubclass(model, pydantic.BaseSettings):
    #     # Hold a reference to the current `parse_env_var` classmethod
    #     parse_env_var = model.__config__.parse_env_var

    #     # Construct a new `parse_env_var` function which suppresses exceptions
    #     # raised by the current `parse_env_var` classmethod. This allows the
    #     # raw values to be passed through to the `pydantic` field validator
    #     # methods if they cannot be parsed initially.
    #     def __parse_env_var(field_name: str, raw_val: str) -> Any:
    #         with contextlib.suppress(Exception):
    #             return parse_env_var(field_name, raw_val)
    #         return raw_val

    #     # Monkeypatch `parse_env_var`
    #     model.__config__.parse_env_var = __parse_env_var  # type: ignore[assignment]

    # Return Constructed Model
    return model


def is_subcommand(model: BaseModel | Type[BaseModel]) -> bool:
    """Check whether the input pydantic Model is a subcommand.

    The default is that all pydantic Models are not subcommands, so this
    has this featured has to be opted in by adding `subcommand=True`
    to the `json_schema_extra` model config. A convenience class has been created
    to provide this default for models that are meant to be command switches at
    the command line: `pydantic_argparse.BaseCommand`.


    Args:
        model (BaseModel | Type[BaseModel]): a pydantic BaseModel subclass

    Returns:
        bool: if the pydantic model is a subcommand
    """
    default = False
    try:
        value = model.model_config["json_schema_extra"].get("subcommand", default)  # type: ignore
        return cast(bool, value)
    except (KeyError, AttributeError):
        # KeyError if:
        #   - subcommand key not in json_schema_extra
        # AttributeError if:
        #   - json_schema_extra not in the model_config, ie if using BaseModel
        # just default to not being a subcommand
        return default
