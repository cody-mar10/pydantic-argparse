"""Declarative and Typed Argument Parser.

The `parser` module contains the `ArgumentParser` class, which provides a
declarative method of defining command-line interfaces.

The procedure to declaratively define a typed command-line interface is:

1. Define `pydantic` arguments model
2. Create typed `ArgumentParser`
3. Parse typed arguments

The resultant arguments object returned is an instance of the defined
`pydantic` model. This means that the arguments object and its attributes will
be compatible with an IDE, linter or type checker.
"""


import argparse
import sys
from typing import Dict, Generic, List, NoReturn, Optional, Type, cast

from pydantic import BaseModel, ValidationError

from pydantic_argparse import parsers, utils
from pydantic_argparse.argparse import (
    actions,
)
from pydantic_argparse.utils.pydantic import PydanticField, PydanticModelT


class ArgumentParser(argparse.ArgumentParser, Generic[PydanticModelT]):
    """Declarative and Typed Argument Parser.

    The `ArgumentParser` declaratively generates a command-line interface using
    the `pydantic` model specified upon instantiation.

    The `ArgumentParser` provides the following `argparse` functionality:

    * Required Arguments
    * Optional Arguments
    * Subcommands

    All arguments are *named*, and positional arguments are not supported.

    The `ArgumentParser` provides the method `parse_typed_args()` to parse
    command line arguments and return an instance of its bound `pydantic`
    model, populated with the parsed and validated user supplied command-line
    arguments.
    """

    # Argument Group Names
    COMMANDS = "commands"
    REQUIRED = "required arguments"
    OPTIONAL = "optional arguments"
    HELP = "help"

    # Keyword Arguments
    KWARG_REQUIRED = "required"

    # Exit Codes
    EXIT_ERROR = 2

    def __init__(
        self,
        model: Type[PydanticModelT],
        prog: Optional[str] = None,
        description: Optional[str] = None,
        version: Optional[str] = None,
        epilog: Optional[str] = None,
        add_help: bool = True,
        exit_on_error: bool = True,
    ) -> None:
        """Instantiates the Typed Argument Parser with its `pydantic` model.

        Args:
            model (Type[PydanticModelT]): Pydantic argument model class.
            prog (Optional[str]): Program name for CLI.
            description (Optional[str]): Program description for CLI.
            version (Optional[str]): Program version string for CLI.
            epilog (Optional[str]): Optional text following help message.
            add_help (bool): Whether to add a `-h`/`--help` flag.
            exit_on_error (bool): Whether to exit on error.
        """
        # Initialise Super Class
        if sys.version_info < (3, 9):  # pragma: <3.9 cover
            super().__init__(
                prog=prog,
                description=description,
                epilog=epilog,
                add_help=False,  # Always disable the automatic help flag.
                argument_default=argparse.SUPPRESS,  # Allow `pydantic` to handle defaults.
            )

        else:  # pragma: >=3.9 cover
            super().__init__(
                prog=prog,
                description=description,
                epilog=epilog,
                exit_on_error=exit_on_error,
                add_help=False,  # Always disable the automatic help flag.
                argument_default=argparse.SUPPRESS,  # Allow `pydantic` to handle defaults.
            )

        # Set Version, Add Help and Exit on Error Flag
        self.version = version
        self.add_help = add_help
        self.exit_on_error = exit_on_error

        # Add Arguments Groups
        self._subcommands: Optional[argparse._SubParsersAction] = None
        # self._required_group = self.add_argument_group(ArgumentParser.REQUIRED)
        # self._optional_group = self.add_argument_group(ArgumentParser.OPTIONAL)
        self._help_group = self.add_argument_group(ArgumentParser.HELP)
        self._arg_groups: dict[str, argparse._ArgumentGroup] = dict()

        # Add Help and Version Flags
        if self.add_help:
            self._add_help_flag()
        if self.version:
            self._add_version_flag()

        # Add Arguments from Model
        self._submodels: dict[str, Type[BaseModel]] = dict()
        self.model = self._add_model(model)

    def parse_typed_args(
        self,
        args: Optional[List[str]] = None,
    ) -> PydanticModelT:
        """Parses command line arguments.

        If `args` are not supplied by the user, then they are automatically
        retrieved from the `sys.argv` command-line arguments.

        Args:
            args (Optional[List[str]]): Optional list of arguments to parse.

        Returns:
            PydanticModelT: Populated instance of typed arguments model.

        Raises:
            argparse.ArgumentError: Raised upon error, if not exiting on error.
            SystemExit: Raised upon error, if exiting on error.
        """
        # Call Super Class Method
        namespace = self.parse_args(args)

        # Convert Namespace to Dictionary
        arguments = utils.namespaces.to_dict(namespace)

        try:
            # check for nested submodels as argument groups
            if self._submodels:
                config = {
                    name: submodel.model_validate(arguments, strict=False)
                    for name, submodel in self._submodels.items()
                }
                return self.model.model_validate(config)
            return self.model.model_validate(arguments)
        except ValidationError as exc:
            # Catch exceptions, and use the ArgumentParser.error() method
            # to report it to the user
            self.error(utils.errors.format(exc))

    # def add_argument(
    #     self,
    #     *args: Any,
    #     **kwargs: Any,
    # ) -> argparse.Action:
    #     """Adds an argument to the ArgumentParser.

    #     Args:
    #         *args (Any): Positional args to be passed to super class method.
    #         **kwargs (Any): Keyword args to be passed to super class method.

    #     Returns:
    #         argparse.Action: Action generated by the argument.
    #     """
    #     # Check whether the argument is required or optional
    #     # We intercept the keyword arguments and "pop" here so that the
    #     # `required` kwarg can never be passed through to the parent
    #     # `ArgumentParser`, allowing Pydantic to perform all of the validation
    #     # and error handling itself.
    #     if kwargs.pop(ArgumentParser.KWARG_REQUIRED):
    #         # Required
    #         group = self._required_group

    #     else:
    #         # Optional
    #         group = self._optional_group

    #     # Return Action
    #     return group.add_argument(*args, **kwargs)

    def error(self, message: str) -> NoReturn:
        """Prints a usage message to `stderr` and exits if required.

        Args:
            message (str): Message to print to the user.

        Raises:
            argparse.ArgumentError: Raised if not exiting on error.
            SystemExit: Raised if exiting on error.
        """
        # Print usage message
        self.print_usage(sys.stderr)

        # Check whether parser should exit
        if self.exit_on_error:
            self.exit(ArgumentParser.EXIT_ERROR, f"{self.prog}: error: {message}\n")

        # Raise Error
        raise argparse.ArgumentError(None, f"{self.prog}: error: {message}")

    def _commands(self) -> argparse._SubParsersAction:
        """Creates and Retrieves Subcommands Action for the ArgumentParser.

        Returns:
            argparse._SubParsersAction: SubParsersAction for the subcommands.
        """
        # Check for Existing Sub-Commands Group
        if not self._subcommands:
            # Add Sub-Commands Group
            self._subcommands = self.add_subparsers(
                title=ArgumentParser.COMMANDS,
                action=actions.SubParsersAction,
                required=True,
            )

            # Shuffle Group to the Top for Help Message
            self._action_groups.insert(0, self._action_groups.pop())

        # Return
        return self._subcommands

    def _add_help_flag(self) -> None:
        """Adds help flag to argparser."""
        # Add help flag
        self._help_group.add_argument(
            "-h",
            "--help",
            action=argparse._HelpAction,
            help="show this help message and exit",
        )

    def _add_version_flag(self) -> None:
        """Adds version flag to argparser."""
        # Add version flag
        self._help_group.add_argument(
            "-v",
            "--version",
            action=argparse._VersionAction,
            help="show program's version number and exit",
        )

    def _add_model(
        self,
        model: Type[PydanticModelT],
        arg_group: Optional[argparse._ArgumentGroup] = None,
    ) -> Type[PydanticModelT]:
        """Adds the `pydantic` model to the argument parser.

        This method also generates "validators" for the arguments derived from
        the `pydantic` model, and generates a new subclass from the model
        containing these validators.

        Args:
            model (Type[PydanticModelT]): Pydantic model class to add to the
                argument parser.
            arg_group: (Optional[argparse._ArgumentGroup]): argparse ArgumentGroup.
                This should not normally be passed manually, but only during
                recursion if the original model is a nested pydantic model. These
                nested models are then parsed as argument groups.

        Returns:
            Type[PydanticModelT]: Pydantic model possibly with new validators.
        """
        # Initialise validators dictionary
        validators: Dict[str, utils.pydantic.PydanticValidator] = dict()
        parser = self if arg_group is None else arg_group

        # Loop through fields in model
        for field in PydanticField.parse_model(model):
            if utils.types.is_field_a(field, BaseModel):
                field_model_type = cast(Type[BaseModel], field.info.annotation)
                if utils.pydantic.is_subcommand(field_model_type):
                    validator = parsers.command.parse_field(self._commands(), field)
                else:
                    # create new arg group
                    group_name = str.upper(field.info.title or field.name)
                    arg_group = self.add_argument_group(group_name)

                    # store group? TODO: idk if needed
                    self._arg_groups[group_name] = arg_group

                    # recurse and parse fields below this submodel
                    self._submodels[field.name] = self._add_model(
                        model=field_model_type,  # type: ignore
                        arg_group=arg_group,
                    )

                    validator = None

            else:
                # Add field
                validator = parsers.add_field(parser, field)

            # Update validators
            utils.pydantic.update_validators(validators, validator)

        # Construct and return model with validators
        return utils.pydantic.model_with_validators(model, validators)
