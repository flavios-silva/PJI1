import asyncio
import selectors
import sys
import uvicorn


def main():
    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )
    server = uvicorn.Server(config)

    if sys.platform == "win32":
        # psycopg3 requires SelectorEventLoop on Windows (ProactorEventLoop breaks async)
        asyncio.run(
            server.serve(),
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
