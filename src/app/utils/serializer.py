from __future__ import annotations

import logging
from collections import deque
from dataclasses import asdict
from dataclasses import is_dataclass
from typing import Any

import orjson
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.utils.configs import SerializationConfig

logger = logging.getLogger(__name__)


class ItemSerializer:
    """
    Fail-safe serializer for logging. Guarantees no exceptions are raised.

    Strategy:
    1. Try orjson first (handles 99% of cases fast)
    2. If orjson fails → iterative Python serialization
    3. If anything fails → return str(obj) or "<unserializable>"
    """

    __slots__ = ("config", "_stats")

    def __init__(self, config: SerializationConfig | None = None) -> None:
        self.config = config or SerializationConfig()
        self._stats: dict[str, int] = {
            "orjson_success": 0,
            "orjson_fallback": 0,
            "max_depth_reached": 0,
            "cycles_detected": 0,
            "fallbacks_triggered": 0,
            "total_objects": 0,
            "errors_caught": 0,
        }

    def serialize(self, obj: Any) -> Any:
        """
        Fail-safe entry point. NEVER raises exceptions.
        Returns serialized object or string fallback.
        """
        try:
            return self._serialize_internal(obj)
        except Exception as e:
            self._stats["errors_caught"] += 1
            logger.error(
                "Serialization failed completely, using fallback: %s",
                str(e)[:200],
                exc_info=False,
            )
            return self._safe_fallback(obj)

    def _serialize_internal(self, obj: Any) -> Any:
        """Internal serialization that may raise exceptions."""
        if self.config.use_orjson:
            try:
                serialized = orjson.loads(
                    orjson.dumps(
                        obj,
                        default=self._orjson_default,
                        option=orjson.OPT_SERIALIZE_NUMPY,
                    )
                )
                self._stats["orjson_success"] += 1
                return serialized

            except (TypeError, ValueError, RecursionError) as e:
                logger.debug(
                    "orjson failed (%s), trying iterative: %s",
                    e.__class__.__name__,
                    str(e)[:100],
                )
                self._stats["orjson_fallback"] += 1

        return self._serialize_iterative(obj)

    def _orjson_default(self, obj: Any) -> Any:
        """Custom handler for orjson for types it doesn't support."""
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")

        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)

        if isinstance(obj, (set, frozenset)):
            return list(obj)

        if hasattr(obj, "isoformat"):
            return obj.isoformat()

        if hasattr(obj, "hex"):
            return obj.hex()

        if hasattr(obj, "__dict__"):
            return obj.__dict__

        # Final fallback for orjson - convert to string
        return str(obj)

    def _serialize_iterative(self, root: Any) -> Any:
        """
        Iterative serialization with cycle detection.
        Soft limits - logs warnings but doesn't raise.
        """
        if self._is_primitive(root):
            return self._serialize_primitive(root)

        stack: deque[tuple[Any, int]] = deque([(root, 0)])
        seen: dict[int, Any] = {}
        processing_order: list[int] = []
        max_depth_seen = 0
        object_count = 0

        while stack:
            current, depth = stack.pop()
            obj_id = id(current)
            object_count += 1

            # Soft limit on object count
            if object_count > self.config.max_objects:
                logger.warning(
                    "Object count limit reached (%d), truncating",
                    self.config.max_objects,
                )
                break

            # Soft limit on depth
            if depth > self.config.max_depth:
                logger.warning(
                    "Depth limit reached (%d), truncating branch",
                    self.config.max_depth,
                )
                seen[obj_id] = "<max_depth_exceeded>"
                continue

            if depth > max_depth_seen:
                max_depth_seen = depth
                if depth >= self.config.warn_depth:
                    logger.debug("Deep nesting detected: depth=%d", depth)

            if self.config.detect_cycles and obj_id in seen:
                self._stats["cycles_detected"] += 1
                continue

            processing_order.append(obj_id)

            try:
                if isinstance(current, BaseModel):
                    seen[obj_id] = current.model_dump(mode="json")
                elif is_dataclass(current) and not isinstance(current, type):
                    seen[obj_id] = asdict(current)
                elif isinstance(current, dict):
                    result: dict[str, Any] = {}
                    for key, val in current.items():
                        str_key = str(key)
                        if self._is_primitive(val):
                            result[str_key] = self._serialize_primitive(val)
                        else:
                            result[str_key] = ("__ref__", id(val))
                            stack.append((val, depth + 1))
                    seen[obj_id] = result
                elif isinstance(current, (list, tuple, set, frozenset)):
                    result_list: list[Any] = []
                    for item in current:
                        if self._is_primitive(item):
                            result_list.append(self._serialize_primitive(item))
                        else:
                            result_list.append(("__ref__", id(item)))
                            stack.append((item, depth + 1))
                    seen[obj_id] = result_list
                else:
                    seen[obj_id] = self._serialize_primitive(current)
            except Exception as e:
                logger.debug("Failed to serialize %s: %s", type(current).__name__, e)
                seen[obj_id] = self._safe_fallback(current)

        # Phase 2: Resolve references
        for obj_id in reversed(processing_order):
            serialized = seen.get(obj_id)
            if serialized is None:
                continue
            if isinstance(serialized, dict):
                for key, val in list(serialized.items()):
                    if isinstance(val, tuple) and len(val) == 2 and val[0] == "__ref__":
                        ref_id = val[1]
                        serialized[key] = seen.get(ref_id, "<unresolved>")
            elif isinstance(serialized, list):
                for i, val in enumerate(serialized):
                    if isinstance(val, tuple) and len(val) == 2 and val[0] == "__ref__":
                        ref_id = val[1]
                        serialized[i] = seen.get(ref_id, "<unresolved>")

        self._stats["max_depth_reached"] = max(
            self._stats["max_depth_reached"], max_depth_seen
        )
        self._stats["total_objects"] += object_count

        return seen.get(id(root), self._safe_fallback(root))

    def _is_primitive(self, obj: Any) -> bool:
        """Check if object is a primitive type."""
        return obj is None or isinstance(obj, (str, int, float, bool))

    def _serialize_primitive(self, obj: Any) -> Any:
        """Serialize primitive types or convert to JSON-compatible."""
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj

        try:
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            if hasattr(obj, "hex"):
                return obj.hex()
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)
        except Exception:
            return self._safe_fallback(obj)

    def _safe_fallback(self, obj: Any) -> str:
        """Ultimate fallback - always returns a string, never raises."""
        try:
            type_name = type(obj).__name__
            return f"<{type_name}>"
        except Exception:
            return "<unserializable>"

    def get_stats(self) -> dict[str, int]:
        """Return serialization statistics."""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        for key in self._stats:
            self._stats[key] = 0


class AdvORJSONResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        assert orjson is not None, "orjson must be installed to use ORJSONResponse"
        return self._serialize_to_bytes(content)

    @classmethod
    def _serialize_to_bytes(cls, obj: Any) -> bytes:
        """Serialize object to bytes for FastAPI Response."""
        try:
            return orjson.dumps(
                obj,
                default=cls._orjson_default,
                option=orjson.OPT_SERIALIZE_NUMPY,
            )
        except (TypeError, ValueError, RecursionError):
            # Fallback: encode string as bytes
            return orjson.dumps(str(obj))

    @staticmethod
    def _orjson_default(obj: Any) -> Any:
        """Custom handler for orjson for types it doesn't support."""
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")

        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)

        if isinstance(obj, (set, frozenset)):
            return list(obj)

        if hasattr(obj, "isoformat"):
            return obj.isoformat()

        if hasattr(obj, "hex"):
            return obj.hex()

        if hasattr(obj, "__dict__"):
            return obj.__dict__

        # Final fallback for orjson - convert to string
        return str(obj)



