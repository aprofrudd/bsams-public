"""Enum definitions for the application."""

from enum import Enum


class Gender(str, Enum):
    """Gender options for athletes."""

    MALE = "male"
    FEMALE = "female"


class UserRole(str, Enum):
    """User role options."""

    COACH = "coach"
    ADMIN = "admin"
