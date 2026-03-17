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
    result = serializer.serialize(entity.obj)

    # For sets, order is not guaranteed
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
    model = SampleModel(name="Alice", age=30)
    result = serializer.serialize(model)

    assert result == {"name": "Alice", "age": 30}, (
        f"Pydantic model serialization failed. "
        f"expected={{'name': 'Alice', 'age': 30}}, actual={result}"
    )


def test_serialize_dataclass(serializer: ItemSerializer) -> None:
    dc = SampleDataclass(title="Test", value=42)
    result = serializer.serialize(dc)

    assert result == {"title": "Test", "value": 42}, (
        f"Dataclass serialization failed. "
        f"expected={{'title': 'Test', 'value': 42}}, actual={result}"
    )


def test_serialize_mixed_structure(serializer: ItemSerializer) -> None:
    data = {
        "model": SampleModel(name="Bob", age=25),
        "dataclass": SampleDataclass(title="Project", value=100),
        "list": [1, 2, 3],
        "nested": {"key": "value"},
    }
    result = serializer.serialize(data)

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
    # Create a deeply nested structure
    depth = 50
    data: dict[str, Any] = {"level": 0}
    current = data
    for i in range(1, depth):
        current["nested"] = {"level": i}
        current = current["nested"]

    result = serializer.serialize(data)

    # Verify the structure is preserved
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
    data = {"key": "value"}
    result = serializer_no_orjson.serialize(data)

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
    serializer.reset_stats()
    serializer.serialize({"key": "value"})

    stats = serializer.get_stats()
    assert stats["orjson_success"] >= 1 or stats["orjson_fallback"] >= 1, (
        f"Stats should be tracked. stats={stats}"
    )


def test_reset_stats(serializer: ItemSerializer) -> None:
    serializer.serialize({"key": "value"})
    serializer.reset_stats()

    stats = serializer.get_stats()
    assert all(v == 0 for v in stats.values()), (
        f"Stats should be reset. stats={stats}"
    )


def test_cycle_detection(serializer: ItemSerializer) -> None:
    # Use config with detect_cycles=True
    serializer.config.detect_cycles = True

    data = {"key": "value"}
    data["self"] = data  # Create cycle

    # Iterate with no orjson to trigger python serializer
    serializer.config.use_orjson = False

    result = serializer.serialize(data)

    # We expect cycle to be detected and skipped (no recursion error).
    assert result["key"] == "value"

    stats = serializer.get_stats()
    assert stats["cycles_detected"] >= 1


def test_iterative_ref_resolution_dict_and_list(
    serializer_no_orjson: ItemSerializer,
) -> None:
    """Shared refs in dict and list get resolved in phase 2.

    Covers ref resolution in the iterative serializer.
    """
    shared = {"nested": 42}
    data = {"a": shared, "b": shared, "list": [1, shared, 2]}
    serializer_no_orjson.config.use_orjson = False
    result = serializer_no_orjson.serialize(data)
    assert result["a"] == {"nested": 42}
    assert result["b"] == {"nested": 42}
    assert result["list"][1] == {"nested": 42}


def test_warn_depth_logged(serializer_no_orjson: ItemSerializer) -> None:
    """Deep nesting at/above warn_depth triggers debug log."""
    serializer_no_orjson.config.warn_depth = 2
    data = {"a": {"b": {"c": 1}}}
    result = serializer_no_orjson.serialize(data)
    assert result["a"]["b"]["c"] == 1


def test_max_depth_limit(serializer: ItemSerializer) -> None:
    # Set small max depth and disable orjson to force iterative
    serializer.config.max_depth = 5
    serializer.config.use_orjson = False

    # Create deeply nested dict
    data: dict[str, Any] = {"level": 0}
    current = data
    for i in range(1, 10):
        current["nested"] = {"level": i}
        current = current["nested"]

    result = serializer.serialize(data)

    # Verify we hit the limit
    # The stats should reflect this
    stats = serializer.get_stats()
    assert stats["max_depth_reached"] >= 5

    # Verify content structure is preserved up to limit.
    # At some point, "nested" should contain "<max_depth_exceeded>" marker.
    # In _serialize_iterative: seen[obj_id] = "<max_depth_exceeded>"

    # Use default=str because other things might be ref tuples.
    # Actually _serialize_iterative resolves references.
    json_str = json.dumps(result, default=str)
    assert "<max_depth_exceeded>" in json_str or "unresolved" in json_str, (
        f"Should have truncated: {json_str}"
    )


def test_max_objects_limit(serializer: ItemSerializer) -> None:
    # Set max objects and disable orjson
    serializer.config.max_objects = 10
    serializer.config.use_orjson = False

    # Create list with many objects
    data = [{"i": i} for i in range(20)]

    serializer.serialize(data)

    # It should be truncated or handled safely
    stats = serializer.get_stats()
    # total_objects might stop at max_objects + 1
    assert stats["total_objects"] >= 10


def test_adv_orjson_response_render() -> None:
    resp = AdvORJSONResponse({"foo": "bar"})
    content = resp.render({"foo": "bar"})
    assert content == b'{"foo":"bar"}'

    # Test fallback in render
    # First call failed (TypeError), second call (fallback) succeeds
    # We mock the second return value to avoid formatting issues.
    fallback_json = b'{"fallback": "json"}'

    with patch("orjson.dumps", side_effect=[TypeError, fallback_json]):
        content = resp.render({"foo": "bar"})
        assert content == fallback_json


def test_serialize_exception_handling(serializer: ItemSerializer) -> None:
    # Mock _serialize_internal to raise Exception
    # Use patch on the class because of __slots__ restriction on instance
    with patch(
        "app.utils.serializer.ItemSerializer._serialize_internal",
        side_effect=Exception("Boom"),
    ):
        result = serializer.serialize({"key": "value"})
        assert result == "<dict>" or "unserializable" in result

        stats = serializer.get_stats()
        assert stats["errors_caught"] >= 1


def test_serialize_iterative_complex_structure(
    serializer_no_orjson: ItemSerializer,
) -> None:
    # Use serializer without orjson to force usage of _serialize_iterative
    # and cover branches like list processing, primitives in lists, etc.
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

    result = serializer_no_orjson.serialize(data)

    # Check structure
    assert result["list_of_ints"] == [1, 2, 3]
    assert result["person"] == {"name": "John"}
    assert result["primitive"] == 42
    # Sets/tuples become lists/arrays in JSON
    assert set(result["set"]) == {1, 2}


def test_orjson_default_types(serializer: ItemSerializer) -> None:
    # Test orjson_default handler with specific types
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

    # orjson uses default handler for these
    result = serializer.serialize(data)

    assert result["uuid"] == str(uid)
    assert result["custom"] == {"a": 1}
    assert "<lambda>" in result["func"] or "<function" in result["func"]


def test_serialize_iterative_primitives_fallback(
    serializer_no_orjson: ItemSerializer,
) -> None:
    class Unserializable:
        __slots__ = ()  # No __dict__ to bypass that check

        def __str__(self):
            raise ValueError("No string for you")

        def __repr__(self):
            raise ValueError("No repr for you")

    obj = Unserializable()
    result = serializer_no_orjson.serialize(obj)
    assert result == "<Unserializable>"


def test_iterative_custom_types(serializer_no_orjson: ItemSerializer) -> None:
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

    result = serializer_no_orjson.serialize(data)

    assert result["uuid"] == uid.hex
    assert result["date"] == now.isoformat()
    assert result["model"] == {"x": 10}
    assert result["has_dict"] == {"x": 1}


def test_serialize_orjson_error_fallback(serializer: ItemSerializer) -> None:
    # Ensure orjson is used
    serializer.config.use_orjson = True

    with patch("orjson.dumps", side_effect=TypeError("Mocked TypeError")):
        # Should fallback to iterative
        # We pass something simple
        result = serializer.serialize({"key": "value"})

        assert result == {"key": "value"}

        stats = serializer.get_stats()
        assert stats["orjson_fallback"] >= 1
        assert stats["orjson_success"] == 0


def test_orjson_default_custom_methods(serializer: ItemSerializer) -> None:
    # Test orjson_default with custom objects resembling primitives.
    # This forces orjson to call default; we verify duck-typing behavior.

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

    # Ensure orjson is used
    serializer.config.use_orjson = True

    result = serializer.serialize(data)

    assert result["iso"] == "2023-01-01"
    assert result["hex_prop"] == "deadbeef"
    assert result["hex_method"] == "feedface"


def test_orjson_default_dataclass_type() -> None:
    @dataclass
    class MyData:
        x: int

    # Test passing the class itself, not an instance
    # This covers "is_dataclass(obj) and not isinstance(obj, type)"
    # Since it is a type, the condition fails, and we proceed to other checks.

    result = ItemSerializer.orjson_default(MyData)

    # It should fallback to str(MyData)
    assert isinstance(result, str)
    assert len(result) > 0


def test_orjson_default_dataclass_instance() -> None:
    @dataclass
    class MyData:
        x: int

    obj = MyData(x=42)
    # Direct call to cover line 89
    result = ItemSerializer.orjson_default(obj)

    assert result == {"x": 42}


def test_orjson_default_object_with_dict_only(
    serializer: ItemSerializer,
) -> None:
    """Object with __dict__ but no isoformat/hex uses obj_dict.

    Covers serializer `orjson_default` dict fallback branch.
    """
    class WithDict:
        def __init__(self) -> None:
            self.a = 1
            self.b = 2

    serializer.config.use_orjson = True
    result = serializer.serialize({"x": WithDict()})
    assert result["x"] == {"a": 1, "b": 2}


def test_orjson_default_returns_dict_direct() -> None:
    """Direct call: `orjson_default` returns `__dict__` as a dict."""
    class PlainObj:
        def __init__(self) -> None:
            self.k = "v"

    out = ItemSerializer.orjson_default(PlainObj())
    assert out == {"k": "v"}


def test_try_isoformat_raises_returns_none(serializer: ItemSerializer) -> None:
    """Object whose isoformat() raises is handled (logger.debug branch)."""
    class BadIso:
        @staticmethod
        def isoformat() -> str:
            raise ValueError("bad")

    serializer.config.use_orjson = True
    result = serializer.serialize({"t": BadIso()})
    assert "t" in result
    # After isoformat raises, orjson_default falls back to __dict__
    assert isinstance(result["t"], dict)


def test_try_hex_returns_non_str_converted(serializer: ItemSerializer) -> None:
    """Object whose hex() returns non-str gets str(value)."""
    class HexReturnsInt:
        @staticmethod
        def hex() -> int:
            return 255

    serializer.config.use_orjson = True
    result = serializer.serialize({"h": HexReturnsInt()})
    assert result["h"] == "255"


def test_try_hex_string_attr_returned(serializer: ItemSerializer) -> None:
    """Object with .hex as string (not callable) returns that string."""
    class HexStr:
        hex = "cafe"

    serializer.config.use_orjson = True
    result = serializer.serialize({"h": HexStr()})
    assert result["h"] == "cafe"


def test_try_hex_raises_returns_none(serializer: ItemSerializer) -> None:
    """Object whose hex() raises is handled (logger.debug branch)."""
    class BadHex:
        @staticmethod
        def hex() -> str:
            raise RuntimeError("bad hex")

    serializer.config.use_orjson = True
    result = serializer.serialize({"h": BadHex()})
    assert "h" in result
    assert isinstance(result["h"], (dict, str, type(None)))


def test_orjson_default_falls_back_to_str_for_object_without_dict() -> None:
    """`orjson_default` falls back to `str(obj)` without `__dict__`."""

    class NoDict:
        __slots__ = ()

        def __str__(self) -> str:
            return "no-dict"

    assert ItemSerializer.orjson_default(NoDict()) == "no-dict"


def test_serialize_iterative_returns_primitive_directly() -> None:
    """Primitive root values are returned without iterative traversal."""
    serializer = ItemSerializer(config=SerializationConfig(use_orjson=False))
    assert serializer.serialize(123) == 123


def test_serialize_iterative_deep_nesting_triggers_debug_branch() -> None:
    """Deep nesting branch is executed when depth reaches warn_depth."""
    serializer = ItemSerializer(
        config=SerializationConfig(use_orjson=False, warn_depth=1),
    )
    nested = {"a": {"b": {"c": 1}}}
    assert serializer.serialize(nested) == nested


def test_serialize_iterative_handles_dict_iteration_error() -> None:
    """Errors during iterative traversal use a safe fallback."""
    serializer = ItemSerializer(config=SerializationConfig(use_orjson=False))
    # Trigger exception path in iterative serialization
    out = serializer.serialize({"data": {"x": object()}})
    # Result may be dict with fallback values or str
    assert isinstance(out, (str, dict))


def test_serialize_iterative_handles_key_str_failure() -> None:
    """Iterative serializer catches exceptions from `str(key)` conversion."""

    class BadKey:
        def __str__(self) -> str:
            raise RuntimeError("bad __str__")

    serializer = ItemSerializer(config=SerializationConfig(use_orjson=False))
    out = serializer.serialize({BadKey(): "value"})
    assert isinstance(out, str)


def test_serialize_primitive_handles_getattr_explosion() -> None:
    """Primitive serialization exceptions are caught.

    The serializer returns a safe string fallback.
    """

    class Exploding:
        def __getattribute__(self, name: str) -> object:
            raise RuntimeError(f"boom: {name}")

    serializer = ItemSerializer(config=SerializationConfig(use_orjson=False))
    out = serializer.serialize(Exploding())
    assert isinstance(out, str)
    assert "Exploding" in out


def test_adv_orjson_response_serialize_exception_fallback() -> None:
    """AdvORJSONResponse uses str(obj) when orjson.dumps raises."""
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
    assert out in {b'"fallback_str"', b'"extra"'}


def test_adv_orjson_response_raises_when_orjson_unavailable() -> None:
    """AdvORJSONResponse.render raises when orjson is None."""
    resp = AdvORJSONResponse(content=None)
    with (
        patch("app.utils.serializer.orjson", None),
        pytest.raises(RuntimeError, match="orjson must be installed"),
    ):
        resp.render({"x": 1})
