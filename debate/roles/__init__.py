"""Role adapters — one per debate agent."""

from debate.roles.base import BaseRole
from debate.roles.bootstrapper import Bootstrapper
from debate.roles.market_analyst import MarketAnalyst
from debate.roles.automation_architect import AutomationArchitect
from debate.roles.devils_advocate import DevilsAdvocate
from debate.roles.moderator import Moderator

ROLE_REGISTRY: dict[str, type[BaseRole]] = {
    "bootstrapper": Bootstrapper,
    "market_analyst": MarketAnalyst,
    "automation_architect": AutomationArchitect,
    "devils_advocate": DevilsAdvocate,
    "moderator": Moderator,
}

__all__ = [
    "BaseRole",
    "Bootstrapper",
    "MarketAnalyst",
    "AutomationArchitect",
    "DevilsAdvocate",
    "Moderator",
    "ROLE_REGISTRY",
]
