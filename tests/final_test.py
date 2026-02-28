from dataclasses import dataclass
from typing import Any, Dict, List

__all__ = ["User", "BaseModel", "create_user", "process_users"]
"""Final test module."""


def placeholder():
    pass


class BaseModel:
    """Base model class"""


@dataclass
class User(BaseModel):
    """用户模型"""

    __slots__ = ("id", "name", "email")
    count: int = 0
    id: int
    name: str

    def __init__(self, id: int, name: str, email: str = ""):
        self.id = id
        self.name = name
        self.email = email
        User.count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "email": self.email}


def create_user(name: str, email: str) -> User:
    """创建新用户"""
    user_id = User.count + 1
    return User(id=user_id, name=name, email=email)


def process_users(users: List[User], /, *, filter_fn: callable = None) -> List[Dict]:
    results = []
    for user in users:
        if filter_fn is None or filter_fn(user):
            results.append(user.to_dict())
    return results
