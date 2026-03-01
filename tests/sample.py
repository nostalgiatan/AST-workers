from datetime import datetime

"""Sample module for testing ast-py CLI."""


def legacy_func():
    """Old function updated"""
    pass


class User:
    __slots__ = ("id", "name", "email")
    count: int = 0
    pass


def new_func(x: int, y: int) -> int:
    return x + y


class Admin(User):
    """Admin user"""

    role: str


def helper(x: str) -> str:
    return x.upper()


def first():
    pass


def second():
    pass


def third():
    pass


def calculate_sum(a: int, b: int) -> int:
    return a + b


def get_timestamp() -> datetime:
    return datetime.now()


def greet(name: str, greeting: str = "Hello") -> str:
    """Generate a greeting message"""
    return f"{greeting}, {name}!"


def test_structured():
    x = 1
    if x > 0:
        print("positive")
    else:
        print("non-positive")


def test_simple():
    pass


def test_batch():
    pass
def test_function(x: int, y: str = 'hello') -> bool:
    if x < 0:
        raise ValueError("x must be positive")
    return x > 0
