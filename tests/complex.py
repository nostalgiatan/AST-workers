"""Complex module for testing nested structures."""

from functools import wraps
from typing import Dict, List, Optional


def retry(times: int):
    """Retry decorator for testing."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise
            return None
        return wrapper
    return decorator


class OuterClass:
    """Outer class with nested structures."""

    instance_count: int = 0

    class InnerClass:
        """Nested class."""

        value: int = 0

        def inner_method(self) -> str:
            return "inner"

    def outer_method(self, filter_fn: callable = None) -> Optional[Dict[str, any]]:
        """Method with complex logic."""

        def helper(x: int) -> int:
            return x * 2

        result = {}
        for i in range(10):
            if i % 2 == 0:
                result[str(i)] = helper(i)

        return result if result else None

    def __repr__(self) -> str:
        return f"OuterClass(instance_count={self.instance_count})"


def complex_function(
    data: Dict[str, List[int]], /, *, transform: Optional[callable] = None, **kwargs
) -> List[Dict[str, any]]:
    results = []
    for key, values in data.items():
        if transform:
            values = [transform(v) for v in values]
        results.append({"key": key, "values": values})
    return results


@retry(3)
async def async_processor(items: List[str]) -> List[dict]:
    results = []
    for item in items:
        results.append({"processed": item})
    return results
