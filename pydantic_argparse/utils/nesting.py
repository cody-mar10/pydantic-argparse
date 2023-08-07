"""Utilities to help with parsing arbitrarily nested `pydantic` models."""

from argparse import Namespace
from typing import Any, Dict, Generic, Optional, Tuple, Type

from boltons.iterutils import get_path, remap
from pydantic import BaseModel

from .namespaces import to_dict
from .pydantic import PydanticField, PydanticModelT


class _ArgumentTree:
    """Simple wrapper for traversing tree-like nested dictionaries."""

    def __init__(self, tree: Dict[str, Any]):
        self._tree = tree

    def __getitem__(self, key: Tuple):
        return get_path(self._tree, key)

    def get(self, key: Tuple, default: Any = None):
        return get_path(self._tree, key, default)

    def __repr__(self) -> str:
        return repr(self._tree)


ModelT = PydanticModelT | Type[PydanticModelT] | BaseModel | Type[BaseModel]


class _NestedArgumentParser(Generic[PydanticModelT]):
    """Parses arbitrarily nested `pydantic` models and inserts values passed at the command line."""

    def __init__(
        self, model: PydanticModelT | Type[PydanticModelT], namespace: Namespace
    ) -> None:
        self.model = model
        self.args = to_dict(namespace)
        self.arg_tree = _ArgumentTree(self.args)
        self.subcommand = False
        self.schema: Dict[str, Any] = self._remove_null_leaves(
            self._get_nested_model_fields(self.model)
        )

        if self.subcommand:
            # if there are subcommands, they should only be in the topmost
            # level, and the way that the unnesting works is
            # that it will populate all subcommands,
            # so we need to remove the subcommands that were
            # not passed at cli

            # the command should be the very first argument
            # after executable/file name
            command = list(self.args.keys())[0]
            self.schema = self._unset_subcommands(self.schema, command)

    def _get_nested_model_fields(self, model: ModelT, parent: Optional[Tuple] = None):
        model_fields: Dict[str, Any] = dict()

        for field in PydanticField.parse_model(model):
            key = field.name

            if field.is_a(BaseModel):
                if field.is_subcommand():
                    self.subcommand = True

                new_parent = (*parent, key) if parent is not None else (key,)

                # recursively build nestes pydantic models in dict,
                # which matches the actual schema the nested
                # schema pydantic will be expecting
                model_fields[key] = self._get_nested_model_fields(
                    field.model_type, new_parent
                )
            else:
                # start with all leaves as None
                value = self.args.get(key, None)
                if parent is not None:
                    # however, if travesing nested models,
                    # then the parent should not be None
                    # and then there is potentially a real
                    # value to get
                    path = (*parent, key)
                    value = self.arg_tree.get(path, value)
                model_fields[key] = value

        return model_fields

    def _remove_null_leaves(self, schema: Dict[str, Any]):
        return remap(schema, visit=lambda p, k, v: v is not None)

    def _unset_subcommands(self, schema: Dict[str, Any], command: str):
        return {key: value for key, value in schema.items() if key == command}

    def validate(self):
        """Return an instance of the `pydantic` modeled validated with data passed from the command line."""
        return self.model.model_validate(self.schema)
