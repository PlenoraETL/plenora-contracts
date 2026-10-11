"""A harness that runs the complete gate once per mutation of one input file
(decision 0021): the message sentinels and the null fuzz.

The inputs are every file the gate reads, found by intercepting each read
during a first, unmutated run: JSON documents and Markdown texts alike,
whatever function reads them (`open`, `Path.open`, `Path.read_text`,
`Path.read_bytes`). A mutation replaces the bytes of one file; every read of
that file, by any reader, sees the mutated bytes.

Running the gate thousands of times is affordable because a validator that
`run_gate` calls is re-executed only when its result can change: when it read
the mutated file in the unmutated run, or when its arguments differ from that
run. Otherwise its unmutated result is returned. Nothing is skipped: the
gate's output is the same as a complete run, which `check_equivalence`
verifies for every input.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import json
import re
from decimal import Decimal
from pathlib import Path, PurePath
from typing import Any, Callable, Iterator
from unittest.mock import patch

from referencing import Registry

import validate_specs as validator
from json_values import JsonNumber, canonical_text

ROOT = validator.ROOT.resolve()
DATA_DIRECTORIES = ("vectors", "examples")


class Raw:
    """A JSON number kept as its exact text, so that a document re-serialized
    without a change reads exactly as before."""

    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Raw) and other.text == self.text

    def __hash__(self) -> int:
        return hash(self.text)


def parse(text: str) -> Any:
    return json.loads(text, parse_float=Raw, parse_int=Raw)


def serialize(document: Any) -> bytes:
    """Two-space JSON with the exact number texts and a final line feed."""
    numbers: list[str] = []

    def number(value: Any) -> str:
        if isinstance(value, Raw):
            numbers.append(value.text)
            return f"\x00{len(numbers) - 1}\x00"
        raise TypeError("not JSON")

    text = json.dumps(document, indent=2, ensure_ascii=False, default=number)
    text = re.sub(r'"\\u0000(\d+)\\u0000"', lambda match: numbers[int(match.group(1))], text)
    return (text + "\n").encode("utf-8")


def _children(value: Any, prefix: tuple[Any, ...]) -> Iterator[tuple[tuple[Any, ...], Any]]:
    if isinstance(value, dict):
        return ((prefix + (key,), child) for key, child in value.items())
    if isinstance(value, list):
        return ((prefix + (index,), child) for index, child in enumerate(value))
    return iter(())


def members(value: Any, prefix: tuple[Any, ...] = ()) -> Iterator[tuple[Any, ...]]:
    """Every object member and every array element, at any depth, in
    document order; walked with an explicit stack, never by recursion."""
    stack = [_children(value, prefix)]
    while stack:
        found = next(stack[-1], None)
        if found is None:
            stack.pop()
            continue
        path, child = found
        yield path
        stack.append(_children(child, path))


def is_data(path: Path) -> bool:
    """A JSON vector or example; any other input, the Markdown next to them
    included, is a contract document."""
    return path.suffix == ".json" and path.relative_to(ROOT).parts[0] in DATA_DIRECTORIES


class Gate:
    """The gate under interception. Use as a context manager."""

    def __init__(self) -> None:
        self.original: dict[Path, bytes] = {}
        self.target: tuple[Path, bytes] | None = None
        self.baseline_run = True
        self.reads: dict[str, set[Path]] = {}
        self.results: dict[str, tuple[tuple[Any, ...], dict[str, Any], Any]] = {}
        self.active: list[str] = []
        self.parsed: dict[str, Any] = {}
        self.shared: set[int] = set()
        self.verdicts: dict[Any, list[str]] = {}
        # A registry's content, by the registry kept alive: an `id` alone
        # could be reused by the registry of a later run.
        self.registries: dict[int, tuple[Any, Any]] = {}
        self.checked: set[int] = set()
        self.target_texts: set[str] = set()
        self.resolved: dict[str, Path | None] = {}
        # False runs every validator: the oracle of the memoized path.
        self.memo = True
        self._stack: contextlib.ExitStack | None = None

    # --- reading ---------------------------------------------------------

    def _resolve(self, file: Any) -> Path | None:
        """The repository file `file` names, or None; resolved once per
        spelling (the files do not move during the test)."""
        try:
            key = str(Path(file))
        except TypeError:
            return None
        if key not in self.resolved:
            path = Path(key).resolve()
            try:
                path.relative_to(ROOT)
            except ValueError:
                path = None
            self.resolved[key] = path if path is not None and path.is_file() else None
        return self.resolved[key]

    def _bytes(self, file: Any) -> bytes | None:
        path = self._resolve(file)
        if path is None:
            return None
        for name in self.active:
            self.reads[name].add(path)
        if self.target is not None and path == self.target[0]:
            return self.target[1]
        if path not in self.original:
            with self._real_open(path, "rb") as handle:
                self.original[path] = handle.read()
        return self.original[path]

    def _open(self, file: Any, mode: str = "r", buffering: int = -1, encoding: str | None = None,
              errors: str | None = None, newline: str | None = None, *args: Any, **kwargs: Any) -> Any:
        content = self._bytes(file) if set(mode) <= {"r", "b", "t"} else None
        if content is None:
            return self._real_open(file, mode, buffering, encoding, errors, newline, *args, **kwargs)
        if "b" in mode:
            return io.BytesIO(content)
        return io.TextIOWrapper(io.BytesIO(content), encoding=encoding or "utf-8", errors=errors,
                                newline=newline)

    def _path_open(self, path: Path, mode: str = "r", buffering: int = -1, encoding: str | None = None,
                   errors: str | None = None, newline: str | None = None) -> Any:
        return self._open(path, mode, buffering, encoding, errors, newline)

    def _read_text(self, path: Path, encoding: str | None = None, errors: str | None = None,
                   newline: str | None = None) -> str:
        with self._open(path, "r", encoding=encoding, errors=errors, newline=newline) as handle:
            return handle.read()

    def _read_bytes(self, path: Path) -> bytes:
        with self._open(path, "rb") as handle:
            return handle.read()

    # --- memoization -----------------------------------------------------

    def _loads(self, text: str) -> Any:
        """Unchanged texts parse to one shared object, which the gate must
        not mutate (`check_unmutated`). The complete run parses every text."""
        if not self.memo:
            return self._real_loads(text)
        if text in self.parsed:
            return self.parsed[text]
        document = self._real_loads(text)
        if self.target is None or text not in self.target_texts:
            self.parsed[text] = document
            self.shared.add(id(document))
        return document

    def _content(self, document: Any) -> Any:
        """A key for a document: its identity when it is shared (unchanged,
        never mutated), otherwise its whole text. The text keeps the member
        order, which orders the errors of a verdict, and the JSON type of
        every value (`1`, `1.0` and `true` differ; a number by its exact
        text), written with an explicit stack (`canonical_text`), so a
        document deeper than the recursion limit has a key too."""
        if id(document) in self.shared:
            return ("shared", id(document))
        return ("text", canonical_text(document, sort_keys=False, by_value=False))

    def _registry_key(self, registry: Any) -> Any:
        """Every schema a `$ref` can reach: a mutation of a referenced schema
        changes the verdict of a schema that refers to it."""
        entry = self.registries.get(id(registry))
        if entry is None or entry[0] is not registry:
            key = tuple(sorted((uri, self._content(registry[uri].contents)) for uri in registry))
            entry = (registry, key)
            self.registries[id(registry)] = entry
        return entry[1]

    def _instance_errors(self, schema: Any, instance: Any, registry: Any) -> list[str]:
        if not self.memo:
            # The oracle of the memoized path computes every verdict.
            return self._real_instance_errors(schema, instance, registry)
        key = (self._content(schema), self._content(instance), self._registry_key(registry))
        if key not in self.verdicts:
            self.verdicts[key] = self._real_instance_errors(schema, instance, registry)
        return list(self.verdicts[key])

    def _check_schema(self, schema: Any, *args: Any, **kwargs: Any) -> None:
        if not self.memo:
            self._real_check_schema(schema, *args, **kwargs)
            return
        if id(schema) in self.shared and id(schema) in self.checked:
            return
        self._real_check_schema(schema, *args, **kwargs)
        if id(schema) in self.shared:
            self.checked.add(id(schema))

    def _wrap(self, name: str, function: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if self.memo and not self.baseline_run and name in self.results:
                before_args, before_kwargs, result = self.results[name]
                unchanged = self.target is not None and self.target[0] not in self.reads[name]
                if unchanged and _same(args, before_args) and _same(kwargs, before_kwargs):
                    return _copy(result)
            self.reads.setdefault(name, set())
            self.active.append(name)
            try:
                result = function(*args, **kwargs)
            finally:
                self.active.pop()
            if self.baseline_run:
                self.results[name] = (args, kwargs, _copy(result))
            return result

        return wrapped

    # --- running ---------------------------------------------------------

    def __enter__(self) -> "Gate":
        self._real_open = builtins.open
        self._real_loads = validator.loads_json
        self._real_instance_errors = validator.instance_errors
        self._real_check_schema = validator.Draft202012Validator.check_schema
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(builtins, "open", self._open))
        stack.enter_context(patch.object(io, "open", self._open))
        stack.enter_context(patch.object(Path, "open", lambda path, *a, **k: self._path_open(path, *a, **k)))
        stack.enter_context(patch.object(Path, "read_text", lambda path, *a, **k: self._read_text(path, *a, **k)))
        stack.enter_context(patch.object(Path, "read_bytes", lambda path: self._read_bytes(path)))
        # A mutation changes the content of one file, never which files
        # exist: listings and existence are read once.
        listings: dict[Any, list[Path]] = {}
        existing: dict[str, bool] = {}
        real_glob, real_rglob, real_exists = Path.glob, Path.rglob, Path.exists

        def listed(kind: str, real: Callable[..., Any]) -> Callable[..., Any]:
            def listing(path: Path, pattern: str, *args: Any, **kwargs: Any) -> Iterator[Path]:
                key = (kind, str(path), pattern, args, tuple(sorted(kwargs.items())))
                if key not in listings:
                    listings[key] = list(real(path, pattern, *args, **kwargs))
                return iter(listings[key])

            return listing

        def exists(path: Path, *args: Any, **kwargs: Any) -> bool:
            key = str(path)
            if args or kwargs:
                return real_exists(path, *args, **kwargs)
            if key not in existing:
                existing[key] = real_exists(path)
            return existing[key]

        stack.enter_context(patch.object(Path, "glob", listed("glob", real_glob)))
        stack.enter_context(patch.object(Path, "rglob", listed("rglob", real_rglob)))
        stack.enter_context(patch.object(Path, "exists", exists))
        stack.enter_context(patch.object(validator, "loads_json", self._loads))
        stack.enter_context(patch.object(validator, "instance_errors", self._instance_errors))
        stack.enter_context(patch.object(validator.Draft202012Validator, "check_schema",
                                         staticmethod(self._check_schema)))
        for name in validator.run_gate.__code__.co_names:
            function = getattr(validator, name, None)
            if callable(function) and getattr(function, "__module__", None) == validator.__name__:
                stack.enter_context(patch.object(validator, name, self._wrap(name, function)))
        self._stack = stack
        self.baseline_output = self.run(None)
        self.baseline_run = False
        return self

    def __exit__(self, *exc: Any) -> None:
        assert self._stack is not None
        self._stack.close()

    def run(self, target: tuple[Path, bytes] | None) -> tuple[Any, str]:
        """The exit status (or the escaping exception) and everything the
        gate printed."""
        self.target = target
        self.target_texts = set()
        if target is not None:
            text = target[1].decode("utf-8", errors="replace")
            self.target_texts = {text, text.replace("\r\n", "\n").replace("\r", "\n")}
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            try:
                status: Any = validator.main()
            except Exception as error:  # noqa: BLE001 - what the fuzzers look for
                status = type(error).__name__
        self.target = None
        return status, out.getvalue() + err.getvalue()

    def run_complete(self, target: tuple[Path, bytes] | None) -> tuple[Any, str]:
        """The same run with every validator executed and without the caches
        of parses, verdicts and schema checks: an independent oracle. Only
        the listings and the existence of files are reused, which a mutation
        never changes."""
        self.memo = False
        try:
            return self.run(target)
        finally:
            self.memo = True

    def inputs(self) -> list[Path]:
        """Every repository file the unmutated run read, in order."""
        return sorted(self.original)

    def check_equivalence(self) -> list[str]:
        """Every JSON input re-serialized unchanged gives the unmutated
        output, and a complete run without memoization gives it too."""
        problems = []
        for path in self.inputs():
            if path.suffix == ".json":
                document = parse(self.original[path].decode("utf-8"))
                if not _same(self.run((path, serialize(document))), self.baseline_output):
                    problems.append(f"{path.relative_to(ROOT).as_posix()} does not re-serialize unchanged")
        return problems

    def check_unmutated(self) -> list[str]:
        """The gate never changed a shared parsed document."""
        return [
            "the gate mutated a shared document"
            for text, document in self.parsed.items()
            if not _same(self._real_loads(text), document)
        ]


def _same(left: Any, right: Any) -> bool:
    """The same data, by type and by value at every depth. Python's `==`
    is not: `1 == True == 1.0`, also inside a dictionary or a list, so a
    schema whose `const` 1 became `true` compared equal to the unmutated
    one and its validators returned the unmutated result."""
    try:
        return _typed_equal(left, right)
    except Exception:  # noqa: BLE001 - an incomparable argument is a different one
        return False


def _typed_equal(left: Any, right: Any) -> bool:
    """The same type and value at every depth, in member order, walked with
    an explicit stack (a document deeper than the recursion limit compares
    like a flat one). The same object is the same value, so an unchanged
    shared document is not walked again."""
    stack = [(left, right)]
    while stack:
        one, other = stack.pop()
        if one is other:
            continue
        kind = type(one)
        if kind is not type(other):
            return False
        if kind is dict:
            if len(one) != len(other):
                return False
            for (key, item), (other_key, other_item) in zip(one.items(), other.items()):
                stack.append((key, other_key))
                stack.append((item, other_item))
        elif kind in (list, tuple):
            if len(one) != len(other):
                return False
            stack.extend(zip(one, other))
        elif kind is Registry:
            # Every schema a `$ref` can reach, as the verdict cache keys it.
            uris = sorted(one)
            if uris != sorted(other):
                return False
            stack.extend((one[uri].contents, other[uri].contents) for uri in uris)
        elif _scalar_image(one) != _scalar_image(other):
            return False
    return True


def _scalar_image(value: Any) -> Any:
    """A typed image of a value that holds no document: a scalar, a set of
    scalars or a path. A value of any other kind is the same only as itself."""
    kind = type(value)
    if value is None or kind in (bool, int, str, bytes):
        return (kind.__name__, value)
    if kind is float:
        # `repr` tells -0.0 from 0.0 and makes a NaN the same as itself.
        return ("float", repr(value))
    if kind is Decimal:
        return ("Decimal", str(value))
    if kind is JsonNumber:
        return ("JsonNumber", value.text)
    if kind is Raw:
        return ("Raw", value.text)
    if kind in (set, frozenset):
        return (kind.__name__, frozenset(_scalar_image(item) for item in value))
    if isinstance(value, PurePath):
        return (kind.__name__, str(value))
    return ("object", id(value))


def _copy(value: Any) -> Any:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, set):
        return set(value)
    return value
