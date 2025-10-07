"""Utility functions for CLI operations."""

def run_async(coro):
    """Helper to run async functions synchronously in Click commands."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)
