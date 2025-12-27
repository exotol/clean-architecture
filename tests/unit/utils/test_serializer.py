from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import BaseModel

from app.utils.configs import SerializationConfig
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
        f"Depth mismatch. "
        f"expected={depth - 1}, actual={level}"
    )


def test_fallback_when_orjson_disabled(serializer_no_orjson: ItemSerializer) -> None:
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
        f"Stats should be tracked. "
        f"stats={stats}"
    )


def test_reset_stats(serializer: ItemSerializer) -> None:
    serializer.serialize({"key": "value"})
    serializer.reset_stats()

    stats = serializer.get_stats()
    assert all(v == 0 for v in stats.values()), (
        f"Stats should be reset. "
        f"stats={stats}"
    )
