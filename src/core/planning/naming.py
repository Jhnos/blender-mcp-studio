"""Every name an instance's objects carry, from one policy.

The V3 generator spelled one station three ways — `F1` for the scene list and
collision groups, `"1"` for the palm cuts, `ARM_1` for a mount frame — in three
functions, each correct on its own. A contract could name a station one way and
the scene another, and nothing would connect them. Here there is one spelling.

The namespace is also what `run_generator` clears by. Two instances sharing a
prefix would erase each other, so each instance gets its own and the registry
test refuses two that overlap.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NamingPolicy:
    #: What `run_generator(build, prefix=...)` clears: letters ending in one underscore.
    namespace: str
    #: The instance family inside that namespace, e.g. `V3`.
    family: str

    def __post_init__(self) -> None:
        stem = self.namespace[:-1]
        if not stem or not stem.isalnum() or not self.namespace.endswith("_"):
            raise ValueError("a namespace is letters or digits ending in one underscore, like 'HJ_'")
        if not self.family or not self.family.isalnum():
            raise ValueError("a family is letters or digits with no underscores, like 'V3'")

    # ------------------------------------------------------------ prefixes

    @property
    def prefix(self) -> str:
        return f"{self.namespace}{self.family}_"

    @property
    def phalanx_prefix(self) -> str:
        return f"{self.prefix}PHALANX_"

    @property
    def hand_prefix(self) -> str:
        return f"{self.prefix}HAND_"

    @property
    def layout_prefix(self) -> str:
        return f"{self.prefix}LAYOUT_PART_"

    @property
    def layout_collection(self) -> str:
        return f"{self.prefix}LAYOUT"

    @property
    def finger_collection(self) -> str:
        return f"{self.prefix}FINGER"

    # -------------------------------------------------------------- objects

    def phalanx(self, index: int) -> str:
        return f"{self.phalanx_prefix}{index}"

    def station_label(self, index: int | None) -> str:
        """`F1`… for the row, `T` for the thumb. The one spelling."""
        return "T" if index is None else f"F{index}"

    def hand_chain_prefix(self, label: str) -> str:
        return f"{self.hand_prefix}{label}_"

    def hand_unit(self, label: str, index: int) -> str:
        return f"{self.hand_chain_prefix(label)}{index}"

    def palm(self) -> str:
        return f"{self.prefix}PALM"

    def thenar(self) -> str:
        return f"{self.prefix}THENAR"

    def root(self, label: str) -> str:
        return f"{self.prefix}ROOT_{label}"

    def cut(self, route: str, label: str) -> str:
        """A named through-cut in the palm: the route it carries and the station it serves."""
        return f"{self.prefix}CUT_{route}_{label}"

    def scratch(self, kind: str) -> str:
        """A transient boolean operand: cleared with the namespace, never counted as a part."""
        return f"{self.namespace}{kind}"

    def layout_part(self, index: int) -> str:
        return f"{self.layout_prefix}{index}"

    def scene_key(self, name: str) -> str:
        return f"{self.prefix}{name}"

    def material(self, role: str) -> str:
        return f"{self.prefix}{role}"
