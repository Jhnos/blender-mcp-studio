"""Build a complete same-part printable product from a restored native execution."""

from typing import Protocol

from src.core.domain.native_revision import NativePrintProduct, NativeRevisionResult


class NativeProductPort(Protocol):
    async def build(self, result: NativeRevisionResult) -> NativePrintProduct: ...
