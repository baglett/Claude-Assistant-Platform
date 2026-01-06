#!/usr/bin/env python
# =============================================================================
# Application Runner
# =============================================================================
"""
Entry point script for running the Claude Assistant Platform backend.

This script handles Windows-specific event loop configuration required for
psycopg's async support before starting uvicorn.

Usage:
    uv run python run.py
    uv run python run.py --reload
    uv run python run.py --host 0.0.0.0 --port 8000
"""

import argparse
import asyncio
import platform
import selectors
import sys


def create_windows_event_loop() -> asyncio.AbstractEventLoop:
    """
    Create a SelectorEventLoop for Windows.

    Psycopg requires SelectorEventLoop, not the default ProactorEventLoop
    that Windows uses.
    """
    selector = selectors.SelectSelector()
    return asyncio.SelectorEventLoop(selector)


async def run_server(host: str, port: int, reload: bool) -> None:
    """
    Run the uvicorn server.

    Args:
        host: Host to bind to.
        port: Port to bind to.
        reload: Enable auto-reload.
    """
    import uvicorn

    config = uvicorn.Config(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    """
    Main entry point that configures the event loop and starts uvicorn.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Claude Assistant Backend")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    # On Windows, use SelectorEventLoop for psycopg compatibility
    if platform.system() == "Windows":
        # Use asyncio.run with a custom loop factory
        asyncio.run(
            run_server(args.host, args.port, args.reload),
            loop_factory=create_windows_event_loop,
        )
    else:
        # On other platforms, use default event loop
        asyncio.run(run_server(args.host, args.port, args.reload))


if __name__ == "__main__":
    main()
