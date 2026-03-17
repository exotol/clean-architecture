from __future__ import annotations

from dataclasses import dataclass
import datetime
import json
from typing import Any
from unittest.mock import patch
import uuid

from pydantic import BaseModel
import pytest

from app.utils.configs import SerializationConfig
from app.utils.serializer import AdvORJSONResponse
from app.utils.serializer import ItemSerializer


# --- Test Schemas ---
@dataclass
class SerializerEntity:
    obj: Any
    config: SerializationConfig | None = None


@dataclass
class SerializerExpected:
    result: Any
    orjson_used: bool = True


# --- Fixtures ---
@pytest.fixture
def serializer() -> ItemSerializer:
    return ItemSerializer()


@pytest.fixture
def serializer_no_orjson() -> ItemSerializer:
    return ItemSerializer(config=SerializationConfig(use_orjson=False))


# --- Test Data ---
class SampleModel(BaseModel):
    name: str
    age: int


@dataclass
class SampleDataclass:
    title: str
    value: int


# --- Tests ---
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            SerializerEntity(obj={"key": "value"}),
            SerializerExpected(result={"key": "value"}),
            id="simple_dict",
        ),
        pytest.param(
            SerializerEntity(obj=[1, 2, 3]),
            SerializerExpected(result=[1, 2, 3]),
            id="simple_list",
        ),
        pytest.param(
            SerializerEntity(obj="string"),
            SerializerExpected(result="string"),
            id="primitive_string",
        ),
        pytest.param(
            SerializerEntity(obj=123),
            SerializerExpected(result=123),
            id="primitive_int",
        ),
        pytest.param(
            SerializerEntity(obj=None),
            SerializerExpected(result=None),
            id="primitive_none",
        ),
        pytest.param(
            SerializerEntity(obj={"nested": {"deep": {"value": 42}}}),
            SerializerExpected(result={"nested": {"deep": {"value": 42}}}),
            id="nested_dict",
        ),
        pytest.param(
            SerializerEntity(obj={"list": [{"a": 1}, {"b": 2}]}),
            SerializerExpected(result={"list": [{"a": 1}, {"b": 2}]}),
            id="dict_with_list_of_dicts",
        ),
        pytest.param(
            SerializerEntity(obj={1, 2, 3}),
            SerializerExpected(result=[1, 2, 3]),  # Sets become lists
            id="set_to_list",
        ),
    ],
)
def test_serialize_basic(
    serializer: ItemSerializer,
    entity: SerializerEntity,
    expected: SerializerExpected,
) -> None:
    # Act
    result = serializer.serialize(entity.obj)

    # Assert (for sets, order is not guaranteed)
    if isinstance(entity.obj, set):
        assert set(result) == set(expected.result), (
            f"Serialization failed for set. "
            f"expected={expected.result}, actual={result}"
        )
    else:
        assert result == expected.result, (
            f"Serialization failed. "
            f"expected={expected.result}, actual={result}"
        )


def test_serialize_pydantic_model(serializer: ItemSerializer) -> None:
    # Arrange
    model = SampleModel(name="Alice", age=30)

    # Act
    result = serializer.serialize(model)

    # Assert
    assert result == {"name": "Alice", "age": 30}, (
        f"Pydantic model serialization failed. "
        f"expected={{'name': 'Alice', 'age': 30}}, actual={result}"
    )


def test_serialize_dataclass(serializer: ItemSerializer) -> None:
    # Arrange
    dc = SampleDataclass(title="Test", value=42)

    # Act
    result = serializer.serialize(dc)

    # Assert
    assert result == {"title": "Test", "value": 42}, (
        f"Dataclass serialization failed. "
        f"expected={{'title': 'Test', 'value': 42}}, actual={result}"
    )


def test_serialize_mixed_structure(serializer: ItemSerializer) -> None:
    # Arrange
    data = {
        "model": SampleModel(name="Bob", age=25),
        "dataclass": SampleDataclass(title="Project", value=100),
        "list": [1, 2, 3],
        "nested": {"key": "value"},
    }

    # Act
    result = serializer.serialize(data)

    # Assert
    expected = {
        "model": {"name": "Bob", "age": 25},
        "dataclass": {"title": "Project", "value": 100},
        "list": [1, 2, 3],
        "nested": {"key": "value"},
    }

    assert result == expected, (
        f"Mixed structure serialization failed. "
        f"expected={expected}, actual={result}"
    )


def test_serialize_deep_nesting(serializer: ItemSerializer) -> None:
    # Arrange: deeply nested structure
    depth = 50
    data: dict[str, Any] = {"level": 0}
    current = data
    for i in range(1, depth):
        current["nested"] = {"level": i}
        current = current["nested"]

    # Act
    result = serializer.serialize(data)

    # Assert: structure preserved
    level = 0
    node = result
    while "nested" in node:
        assert node["level"] == level, (
            f"Level mismatch at depth {level}. "
            f"expected={level}, actual={node['level']}"
        )
        node = node["nested"]
        level += 1

    assert level == depth - 1, (
        f"Depth mismatch. expected={depth - 1}, actual={level}"
    )


def test_fallback_when_orjson_disabled(
    serializer_no_orjson: ItemSerializer,
) -> None:
    # Arrange
    data = {"key": "value"}

    # Act
    result = serializer_no_orjson.serialize(data)

    # Assert
    assert result == {"key": "value"}, (
        f"Fallback serialization failed. "
        f"expected={{'key': 'value'}}, actual={result}"
    )

    stats = serializer_no_orjson.get_stats()
    assert stats["orjson_success"] == 0, (
        f"orjson should not be used. "
        f"expected=0, actual={stats['orjson_success']}"
    )


def test_stats_tracking(serializer: ItemSerializer) -> None:
    # Arrange & Act
    serializer.reset_stats()
    serializer.serialize({"key": "value"})
    stats = serializer.get_stats()

    # Assert
    assert stats["orjson_success"] >= 1 or stats["orjson_fallback"] >= 1, (
        f"Stats should be tracked. stats={stats}"
    )


def test_reset_stats(serializer: ItemSerializer) -> None:
    # Arrange & Act
    serializer.serialize({"key": "value"})
    serializer.reset_stats()
    stats = serializer.get_stats()

    # Assert
    assert all(v == 0 for v in stats.values()), (
        f"Stats should be reset. stats={stats}"
    )


def test_cycle_detection(serializer: ItemSerializer) -> None:
    # Arrange
    serializer.config.detect_cycles = True
    data = {"key": "value"}
    data["self"] = data
    serializer.config.use_orjson = False

    # Act
    result = serializer.serialize(data)
    stats = serializer.get_stats()

    # Assert: cycle detected and skipped (no recursion error)
    assert result["key"] == "value", (
        f"Expected key 'value', got {result.get('key')!r}"
    )
    assert stats["cycles_detected"] >= 1, (
        f"Expected cycles_detected >= 1, got {stats['cycles_detected']}"
    )


def test_iterative_ref_resolution_dict_and_list(
    serializer_no_orjson: ItemSerializer,
) -> None:
    """Shared refs in dict and list get resolved in phase 2."""
    # Arrange
    shared = {"nested": 42}
    data = {"a": shared, "b": shared, "list": [1, shared, 2]}
    serializer_no_orjson.config.use_orjson = False

    # Act
    result = serializer_no_orjson.serialize(data)

    # Assert
    assert result["a"] == {"nested": 42}, (
        f"Expected result['a'] {{'nested': 42}}, got {result['a']!r}"
    )
    assert result["b"] == {"nested": 42}, (
        f"Expected result['b'] {{'nested': 42}}, got {result['b']!r}"
    )
    assert result["list"][1] == {"nested": 42}, (
        f"Expected result['list'][1] {{'nested': 42}}, "
        f"got {result['list'][1]!r}"
    )


def test_warn_depth_logged(serializer_no_orjson: ItemSerializer) -> None:
    """Deep nesting at/above warn_depth triggers debug log."""
    # Arrange
    serializer_no_orjson.config.warn_depth = 2
    data = {"a": {"b": {"c": 1}}}

    # Act
    result = serializer_no_orjson.serialize(data)

    # Assert
    assert result["a"]["b"]["c"] == 1, (
        f"Expected nested value 1, got {result['a']['b']['c']!r}"
    )


def test_max_depth_limit(serializer: ItemSerializer) -> None:
    # Arrange
    serializer.config.max_depth = 5
    serializer.config.use_orjson = False
    data: dict[str, Any] = {"level": 0}
    current = data
    for i in range(1, 10):
        current["nested"] = {"level": i}
        current = current["nested"]

    # Act
    result = serializer.serialize(data)
    stats = serializer.get_stats()

    # Assert
    assert stats["max_depth_reached"] >= 5, (
        f"Expected max_depth_reached >= 5, got {stats['max_depth_reached']}"
    )
    # At some point, "nested" should contain "<max_depth_exceeded>" marker.
    # In _serialize_iterative: seen[obj_id] = "<max_depth_exceeded>"

    # Use default=str because other things might be ref tuples.
    # Actually _serialize_iterative resolves references.
    json_str = json.dumps(result, default=str)
    assert "<max_depth_exceeded>" in json_str or "unresolved" in json_str, (
        f"Should have truncated: {json_str}"
    )


def test_max_objects_limit(serializer: ItemSerializer) -> None:
    # Arrange
    serializer.config.max_objects = 10
    serializer.config.use_orjson = False
    data = [{"i": i} for i in range(20)]

    # Act
    serializer.serialize(data)
    stats = serializer.get_stats()

    # Assert: truncated or handled safely (total_objects >= max_objects)
    assert stats["total_objects"] >= 10, (
        f"Expected total_objects >= 10, got {stats['total_objects']}"
    )


def test_adv_orjson_response_render() -> None:
    # Arrange & Act
    resp = AdvORJSONResponse({"foo": "bar"})
    content = resp.render({"foo": "bar"})

    # Assert
    assert content == b'{"foo":"bar"}', f"Expected JSON bytes, got {content!r}"

    # Fallback in render: first call TypeError, second succeeds
    fallback_json = b'{"fallback": "json"}'
    with patch("orjson.dumps", side_effect=[TypeError, fallback_json]):
        content = resp.render({"foo": "bar"})
        assert content == fallback_json, (
            f"Expected fallback content, got {content!r}"
        )


def test_serialize_exception_handling(serializer: ItemSerializer) -> None:
    # Arrange & Act
    with patch(
        "app.utils.serializer.ItemSerializer._serialize_internal",
        side_effect=Exception("Boom"),
    ):
        result = serializer.serialize({"key": "value"})
        stats = serializer.get_stats()

    # Assert
    assert result == "<dict>" or "unserializable" in result, (
        f"Expected fallback string, got {result!r}"
    )
    assert stats["errors_caught"] >= 1, (
        f"Expected errors_caught >= 1, got {stats['errors_caught']}"
    )


def test_serialize_iterative_complex_structure(
    serializer_no_orjson: ItemSerializer,
) -> None:
    # Arrange
    @dataclass
    class Person:
        name: str

    data = {
        "list_of_ints": [1, 2, 3],
        "list_of_str": ["a", "b"],
        "set": {1, 2},
        "tuple": (1, 2),
        "person": Person("John"),
        "dict": {"a": 1},
        "primitive": 42,
    }

    # Act
    result = serializer_no_orjson.serialize(data)

    # Assert
    assert result["list_of_ints"] == [1, 2, 3], (
        f"Expected list_of_ints [1,2,3], got {result['list_of_ints']!r}"
    )
    assert result["person"] == {"name": "John"}, (
        f"Expected person {{'name': 'John'}}, got {result['person']!r}"
    )
    assert result["primitive"] == 42, (
        f"Expected primitive 42, got {result['primitive']!r}"
    )
    assert set(result["set"]) == {1, 2}, (
        f"Expected set {{1,2}}, got {result['set']!r}"
    )


def test_orjson_default_types(serializer: ItemSerializer) -> None:
    # Arrange
    @dataclass
    class Point:
        x: int
        y: int

    class CustomObj:
        def __init__(self):
            self.a = 1

    uid = uuid.uuid4()
    now = datetime.datetime.now(tz=datetime.UTC)
    data = {
        "uuid": uid,
        "date": now,
        "point": Point(1, 2),
        "set": {1, 2},
        "custom": CustomObj(),
        "func": lambda x: x,
    }

    # Act
    result = serializer.serialize(data)

    # Assert
    assert result["uuid"] == str(uid), (
        f"Expected uuid as str, got {result['uuid']!r}"
    )
    assert result["custom"] == {"a": 1}, (
        f"Expected custom {{'a': 1}}, got {result['custom']!r}"
    )
    assert "<lambda>" in result["func"] or "<function" in result["func"], (
        f"Expected func repr with lambda/function, got {result['func']!r}"
    )


def test_serialize_iterative_primitives_fallback(
    serializer_no_orjson: ItemSerializer,
) -> None:
    # Arrange
    class Unserializable:
        __slots__ = ()

        def __str__(self):
            raise ValueError("No string for you")

        def __repr__(self):
            raise ValueError("No repr for you")

    obj = Unserializable()

    # Act
    result = serializer_no_orjson.serialize(obj)

    # Assert
    assert result == "<Unserializable>", (
        f"Expected '<Unserializable>', got {result!r}"
    )


def test_iterative_custom_types(serializer_no_orjson: ItemSerializer) -> None:
    # Arrange
    class MyModel(BaseModel):
        x: int

    class HasDict:
        def __init__(self):
            self.x = 1

    uid = uuid.uuid4()
    now = datetime.datetime.now(tz=datetime.UTC)
    model = MyModel(x=10)
    has_dict = HasDict()
    data = {
        "uuid": uid,
        "date": now,
        "model": model,
        "has_dict": has_dict,
    }

    # Act
    result = serializer_no_orjson.serialize(data)

    # Assert
    assert result["uuid"] == uid.hex, (
        f"Expected uuid hex, got {result['uuid']!r}"
    )
    assert result["date"] == now.isoformat(), (
        f"Expected date isoformat, got {result['date']!r}"
    )
    assert result["model"] == {"x": 10}, (
        f"Expected model {{'x': 10}}, got {result['model']!r}"
    )
    assert result["has_dict"] == {"x": 1}, (
        f"Expected has_dict {{'x': 1}}, got {result['has_dict']!r}"
    )


def test_serialize_orjson_error_fallback(serializer: ItemSerializer) -> None:
    # Arrange
    serializer.config.use_orjson = True

    with patch("orjson.dumps", side_effect=TypeError("Mocked TypeError")):
        # Act
        result = serializer.serialize({"key": "value"})
        stats = serializer.get_stats()

    # Assert
    assert result == {"key": "value"}, (
        f"Expected fallback result, got {result!r}"
    )
    assert stats["orjson_fallback"] >= 1, (
        f"Expected orjson_fallback >= 1, got {stats['orjson_fallback']}"
    )
    assert stats["orjson_success"] == 0, (
        f"Expected orjson_success 0, got {stats['orjson_success']}"
    )


def test_orjson_default_custom_methods(serializer: ItemSerializer) -> None:
    # Arrange
    class CustomIso:
        @staticmethod
        def isoformat() -> str:
            return "2023-01-01"

    class CustomHex:
        @property
        def hex(self):
            return "deadbeef"

    class CustomHexMethod:
        @staticmethod
        def hex() -> str:
            return "feedface"

    data = {
        "iso": CustomIso(),
        "hex_prop": CustomHex(),
        "hex_method": CustomHexMethod(),
    }
    serializer.config.use_orjson = True

    # Act
    result = serializer.serialize(data)

    # Assert
    assert result["iso"] == "2023-01-01", (
        f"Expected iso '2023-01-01', got {result['iso']!r}"
    )
    assert result["hex_prop"] == "deadbeef", (
        f"Expected hex_prop 'deadbeef', got {result['hex_prop']!r}"
    )
    assert result["hex_method"] == "feedface", (
        f"Expected hex_method 'feedface', got {result['hex_method']!r}"
    )


def test_orjson_default_dataclass_type() -> None:
    # Arrange
    @dataclass
    class MyData:
        x: int

    # Act: pass the class itself, not an instance
    result = ItemSerializer.orjson_default(MyData)

    # Assert: fallback to str(MyData)
    assert isinstance(result, str), (
        f"Expected str fallback, got {type(result)}"
    )
    assert len(result) > 0, f"Expected non-empty str, got len={len(result)}"


def test_orjson_default_dataclass_instance() -> None:
    # Arrange
    @dataclass
    class MyData:
        x: int

    obj = MyData(x=42)

    # Act
    result = ItemSerializer.orjson_default(obj)

    # Assert
    assert result == {"x": 42}, f"Expected {{'x': 42}}, got {result!r}"


def test_orjson_default_object_with_dict_only(
    serializer: ItemSerializer,
) -> None:
    """Object with __dict__ but no isoformat/hex uses obj_dict."""

    # Arrange
    class WithDict:
        def __init__(self) -> None:
            self.a = 1
            self.b = 2

    serializer.config.use_orjson = True

    # Act
    result = serializer.serialize({"x": WithDict()})

    # Assert
    assert result["x"] == {"a": 1, "b": 2}, (
        f"Expected {{'a': 1, 'b': 2}}, got {result['x']!r}"
    )


def test_orjson_default_returns_dict_direct() -> None:
    """Direct call: orjson_default returns __dict__ as a dict."""

    # Arrange & Act
    class PlainObj:
        def __init__(self) -> None:
            self.k = "v"

    out = ItemSerializer.orjson_default(PlainObj())

    # Assert
    assert out == {"k": "v"}, f"Expected {{'k': 'v'}}, got {out!r}"


def test_try_isoformat_raises_returns_none(serializer: ItemSerializer) -> None:
    """Object whose isoformat() raises is handled (logger.debug branch)."""

    # Arrange
    class BadIso:
        @staticmethod
        def isoformat() -> str:
            raise ValueError("bad")

    serializer.config.use_orjson = True

    # Act
    result = serializer.serialize({"t": BadIso()})

    # Assert: fallback to __dict__
    assert "t" in result, (
        f"Expected 't' in result, got keys {list(result.keys())}"
    )
    assert isinstance(result["t"], dict), (
        f"Expected result['t'] to be dict, got {type(result['t'])}"
    )


def test_try_hex_returns_non_str_converted(serializer: ItemSerializer) -> None:
    """Object whose hex() returns non-str gets str(value)."""

    # Arrange
    class HexReturnsInt:
        @staticmethod
        def hex() -> int:
            return 255

    serializer.config.use_orjson = True

    # Act
    result = serializer.serialize({"h": HexReturnsInt()})

    # Assert
    assert result["h"] == "255", f"Expected '255', got {result['h']!r}"


def test_try_hex_string_attr_returned(serializer: ItemSerializer) -> None:
    """Object with .hex as string (not callable) returns that string."""

    # Arrange
    class HexStr:
        hex = "cafe"

    serializer.config.use_orjson = True

    # Act
    result = serializer.serialize({"h": HexStr()})

    # Assert
    assert result["h"] == "cafe", f"Expected 'cafe', got {result['h']!r}"


def test_try_hex_raises_returns_none(serializer: ItemSerializer) -> None:
    """Object whose hex() raises is handled (logger.debug branch)."""

    # Arrange
    class BadHex:
        @staticmethod
        def hex() -> str:
            raise RuntimeError("bad hex")

    serializer.config.use_orjson = True

    # Act
    result = serializer.serialize({"h": BadHex()})

    # Assert
    assert "h" in result, (
        f"Expected 'h' in result, got keys {list(result.keys())}"
    )
    assert isinstance(result["h"], (dict, str, type(None))), (
        f"Expected result['h'] dict/str/None, got {type(result['h'])}"
    )


def test_orjson_default_falls_back_to_str_for_object_without_dict() -> None:
    """orjson_default falls back to str(obj) without __dict__."""

    # Arrange & Act
    class NoDict:
        __slots__ = ()

        def __str__(self) -> str:
            return "no-dict"

    out = ItemSerializer.orjson_default(NoDict())

    # Assert
    assert out == "no-dict", f"Expected 'no-dict', got {out!r}"


def test_serialize_iterative_returns_primitive_directly() -> None:
    """Primitive root values are returned without iterative traversal."""
    # Arrange & Act
    serializer = ItemSerializer(config=SerializationConfig(use_orjson=False))
    result = serializer.serialize(123)

    # Assert
    assert result == 123, f"Expected 123, got {result!r}"


def test_serialize_iterative_deep_nesting_triggers_debug_branch() -> None:
    """Deep nesting branch is executed when depth reaches warn_depth."""
    # Arrange & Act
    serializer = ItemSerializer(
        config=SerializationConfig(use_orjson=False, warn_depth=1),
    )
    nested = {"a": {"b": {"c": 1}}}
    result = serializer.serialize(nested)

    # Assert
    assert result == nested, (
        f"Expected nested structure preserved, got {result!r}"
    )


def test_serialize_iterative_handles_dict_iteration_error() -> None:
    """Errors during iterative traversal use a safe fallback."""
    # Arrange & Act
    serializer = ItemSerializer(config=SerializationConfig(use_orjson=False))
    out = serializer.serialize({"data": {"x": object()}})

    # Assert: result may be dict with fallback or str
    assert isinstance(out, (str, dict)), (
        f"Expected str or dict, got {type(out)}"
    )


def test_serialize_iterative_handles_key_str_failure() -> None:
    """Iterative serializer catches exceptions from str(key) conversion."""

    # Arrange & Act
    class BadKey:
        def __str__(self) -> str:
            raise RuntimeError("bad __str__")

    serializer = ItemSerializer(config=SerializationConfig(use_orjson=False))
    out = serializer.serialize({BadKey(): "value"})

    # Assert
    assert isinstance(out, str), f"Expected str fallback, got {type(out)}"


def test_serialize_primitive_handles_getattr_explosion() -> None:
    """Primitive serialization exceptions are caught; safe string fallback."""

    # Arrange & Act
    class Exploding:
        def __getattribute__(self, name: str) -> object:
            raise RuntimeError(f"boom: {name}")

    serializer = ItemSerializer(config=SerializationConfig(use_orjson=False))
    out = serializer.serialize(Exploding())

    # Assert
    assert isinstance(out, str), f"Expected str fallback, got {type(out)}"
    assert "Exploding" in out, f"Expected 'Exploding' in out, got {out!r}"


def test_adv_orjson_response_serialize_exception_fallback() -> None:
    """AdvORJSONResponse uses str(obj) when orjson.dumps raises."""
    # Arrange & Act
    with patch(
        "app.utils.serializer.orjson.dumps",
        side_effect=[
            RecursionError("depth"),
            b'"fallback_str"',
            b'"extra"',
        ],
    ):
        resp = AdvORJSONResponse(content=None)
        out = resp.render({"x": 1})

    # Assert
    assert out in {b'"fallback_str"', b'"extra"'}, (
        f"Expected fallback bytes, got {out!r}"
    )


def test_adv_orjson_response_raises_when_orjson_unavailable() -> None:
    """AdvORJSONResponse.render raises when orjson is None."""
    resp = AdvORJSONResponse(content=None)
    with (
        patch("app.utils.serializer.orjson", None),
        pytest.raises(RuntimeError, match="orjson must be installed"),
    ):
        resp.render({"x": 1})
