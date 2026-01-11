from __future__ import annotations

import asyncio
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterator,
    Optional,
    TypeVar,
    cast,
)

from mcp_tool_gateway.mcp_instance import mcp

F = TypeVar("F", bound=Callable[..., Any])

# Cache the *raw Python callable* behind each tool name so unit tests / internal calls
# can invoke logic without going through MCP transport.
_TOOL_CALLABLES: Dict[str, Callable[..., Any]] = {}


@dataclass(frozen=True)
class ToolSpec:
    """Metadata for an MCP tool (for discovery endpoints)."""

    name: str
    description: str


class BaseTool(ABC):
    """Base class for MCP tools.

    Each tool:
      - exposes a ToolSpec via `spec`
      - registers one or more MCP tool functions via `register()`

    Convenience runners:
      - `await run(...)`           -> default async invocation (non-blocking)
      - `run_sync(...)`           -> sync-only invocation (raises if tool is async)
      - `async for x in run_stream(...)` -> streaming invocation (best-effort)
    """

    @property
    @abstractmethod
    def spec(self) -> ToolSpec:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def register(self) -> None:  # pragma: no cover
        """Register tool functions with the shared FastMCP instance."""
        raise NotImplementedError

    # ---------------------------
    # Internal helpers
    # ---------------------------
    def _ensure_fn(self) -> Callable[..., Any]:
        """Ensure tool is registered and a callable exists in cache."""
        fn = _TOOL_CALLABLES.get(self.spec.name)
        if fn is None:
            # run registration so tool_decorator caches the function
            self.register()
            fn = _TOOL_CALLABLES.get(self.spec.name)

        if fn is None:
            raise RuntimeError(
                f"Tool '{self.spec.name}' did not register a callable. "
                "Ensure register() defines a function decorated with "
                "tool_decorator(name=self.spec.name, ...)."
            )
        return fn

    # ---------------------------
    # Public runners
    # ---------------------------
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Default invocation (async).

        - If tool is `async def`, it is awaited.
        - If tool is sync `def`, it is executed in a worker thread so it won't block the event loop.
        """
        fn = self._ensure_fn()
        if inspect.iscoroutinefunction(fn):
            return await fn(*args, **kwargs)

        # Sync tool: run in a thread for non-blocking behavior
        return await asyncio.to_thread(fn, *args, **kwargs)

    def run_sync(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronous invocation.

        - Works only if the tool callable is sync.
        - Raises if the tool callable is async.
        """
        fn = self._ensure_fn()
        if inspect.iscoroutinefunction(fn):
            raise RuntimeError(
                f"Tool '{self.spec.name}' is async; use `await run(...)` instead."
            )
        return fn(*args, **kwargs)

    async def run_async(self, *args: Any, **kwargs: Any) -> Any:
        """Alias for `run()` (kept for clarity/back-compat)."""
        return await self.run(*args, **kwargs)

    async def run_stream(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        """Streaming invocation (async generator), best-effort.

        Supports common streaming styles:
          1) Tool is an async generator function:
                async def tool(...):
                    yield ...
          2) Tool returns an AsyncIterator:
                async def tool(...)->AsyncIterator: return stream
          3) Tool returns an Iterator (sync generator):
                def tool(...):
                    yield ...
             (Iterated in a thread, yielding items back to event loop)
          4) Tool returns a single value (non-stream):
                def/async def tool(...)->Any
             (Yields exactly one item)

        For true token streaming, implement your tool as an async generator
        and `yield` chunks.
        """
        fn = self._ensure_fn()

        # Case 1: async generator function
        if inspect.isasyncgenfunction(fn):
            agen = fn(*args, **kwargs)
            assert hasattr(agen, "__aiter__")
            async for item in cast(AsyncIterator[Any], agen):
                yield item
            return

        # Case 2: coroutine function (async def that returns something)
        if inspect.iscoroutinefunction(fn):
            result = await fn(*args, **kwargs)
            async for item in _coerce_to_async_stream(result):
                yield item
            return

        # Case 3/4: sync function
        # Run the sync function in a thread to avoid blocking.
        result = await asyncio.to_thread(fn, *args, **kwargs)
        async for item in _coerce_to_async_stream(result):
            yield item


def tool_decorator(*, name: str, description: str):
    """Thin wrapper around `mcp.tool()` plus a callable cache for tests/internal runs.

    Keeps tool modules clean (they don't need to import `mcp`).
    Also caches the raw Python callable under `name` so BaseTool.run* can invoke it.
    """
    mcp_deco = mcp.tool(name=name, description=description)  # type: ignore[arg-type]

    def _decorator(fn: F) -> F:
        wrapped = mcp_deco(fn)

        # Cache the *original* function for unit tests / internal execution.
        # (Prefer raw fn over wrapped to avoid transport-specific wrappers.)
        _TOOL_CALLABLES[name] = cast(Callable[..., Any], fn)

        # Return MCP's wrapped callable for proper MCP registration.
        return cast(F, wrapped)

    return _decorator


# ---------------------------
# Streaming coercion helpers
# ---------------------------
async def _coerce_to_async_stream(obj: Any) -> AsyncIterator[Any]:
    """Turn different return shapes into an async stream."""
    # Async iterator
    if hasattr(obj, "__aiter__"):
        async for item in cast(AsyncIterator[Any], obj):
            yield item
        return

    # Sync iterable (generator, list, tuple, etc.)
    # Avoid treating strings/bytes/dicts as streams.
    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, dict)):
        it = iter(obj)  # ✅ convert Iterable -> Iterator
        async for item in _iterate_sync_iterator_in_thread(it):
            yield item
        return

    # Non-stream: yield once
    yield obj


async def _iterate_sync_iterator_in_thread(it: Iterator[Any]) -> AsyncIterator[Any]:
    """Iterate a sync iterator without blocking the event loop."""
    while True:
        try:
            item = await asyncio.to_thread(next, it)
        except StopIteration:
            return
        yield item
