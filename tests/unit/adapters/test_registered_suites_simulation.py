"""RegisteredSuitesSimulation runs suites sequentially, in order."""

import asyncio

from src.adapters.simulation.registered_suites_simulation import RegisteredSuitesSimulation
from src.core.domain.verification import VerificationReport


class FakeVerification:
    def __init__(self) -> None:
        self.log: list[str] = []
        self.active = 0
        self.max_active = 0

    async def list_suites(self):
        return ()

    async def run(self, suite_id: str) -> VerificationReport:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.log.append(f"start-{suite_id}")
        await asyncio.sleep(0.01)
        self.log.append(f"end-{suite_id}")
        self.active -= 1
        return VerificationReport(suite_id, True, (), "scope", True)


async def test_suites_run_sequentially_in_order():
    fake = FakeVerification()
    reports = await RegisteredSuitesSimulation(fake).run(("b", "a", "c"))
    assert [r.suite_id for r in reports] == ["b", "a", "c"]
    assert fake.max_active == 1
    assert fake.log == ["start-b", "end-b", "start-a", "end-a", "start-c", "end-c"]


async def test_no_suites_returns_empty_tuple():
    assert await RegisteredSuitesSimulation(FakeVerification()).run(()) == ()
