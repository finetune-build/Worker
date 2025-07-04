# mcp_http_server_process.py
import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional
import uvicorn
from finetune.processes.base import BaseProcess


class MCPHttpServerProcess(BaseProcess):
    """Simplified process manager for MCP HTTP servers."""
    
    def __init__(
        self,
        # server_file: str = "server.py",
        server_file: str = "examples/mcp_http_server.py",
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = False,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.server_file = server_file
        self.host = host
        self.port = port
        self.reload = reload
        self._server = None
        
    def load_server_app(self):
        """Load the ASGI app from the server file."""
        server_path = Path(self.server_file).resolve()
        
        if not server_path.exists():
            # Try looking in examples directory as fallback
            examples_path = Path("examples") / self.server_file
            if examples_path.exists():
                server_path = examples_path.resolve()
            else:
                raise FileNotFoundError(
                    f"Server file not found: {self.server_file}\n"
                    f"Create a server.py file with your MCP server implementation."
                )
        
        self.logger.info(f"Loading server from: {server_path}")
        
        # Load module from file
        spec = importlib.util.spec_from_file_location("user_mcp_server", server_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["user_mcp_server"] = module
        spec.loader.exec_module(module)
        
        # For simple FastMCP servers (like our examples)
        if hasattr(module, 'mcp'):
            mcp = module.mcp
            # Check if it's already an app or needs conversion
            if hasattr(mcp, 'streamable_http_app'):
                self.logger.info("Found FastMCP server, creating ASGI app")
                return mcp.streamable_http_app()
        
        # For FastAPI/Starlette apps
        if hasattr(module, 'app'):
            self.logger.info("Found ASGI app directly")
            return module.app
        
        raise AttributeError(
            f"No MCP server or ASGI app found in {self.server_file}. "
            "Expected either:\n"
            "  - A FastMCP instance named 'mcp'\n"
            "  - A FastAPI/Starlette app named 'app'"
        )
    
    async def run_server(self):
        """Run the HTTP server."""
        while self.running:
            try:
                app = self.load_server_app()
                
                self.logger.info(f"Starting MCP server on {self.host}:{self.port}")
                
                config = uvicorn.Config(
                    app,
                    host=self.host,
                    port=self.port,
                    reload=self.reload,
                    log_level="info",
                    access_log=False,
                )
                
                self._server = uvicorn.Server(config)
                await self._server.serve()
                
                if self.running:
                    self.logger.warning("Server stopped unexpectedly")
                    await asyncio.sleep(5)  # Simple retry delay
                
            except asyncio.CancelledError:
                self.logger.info("Server cancelled")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")
                if self.running:
                    self.logger.info("Retrying in 5 seconds...")
                    await asyncio.sleep(5)
        
        self.logger.info("Server stopped")
    
    def run(self):
        """Main process loop."""
        try:
            asyncio.run(self.run_server())
        except Exception as e:
            self.logger.error(f"Process error: {e}")
    
    def _shutdown(self, signum: int, frame: Any):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        if self._server:
            self._server.should_exit = True


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP HTTP Server Process")
    parser.add_argument(
        "server_file",
        nargs="?",
        # default="server.py",
        default = "examples/mcp_http_server.py",
        help="Server file to run (default: server.py)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--name", default="mcp-server", help="Process name")
    
    args = parser.parse_args()
    
    process = MCPHttpServerProcess(
        server_file=args.server_file,
        host=args.host,
        port=args.port,
        reload=args.reload,
        name=args.name
    )
    process.start()


if __name__ == "__main__":
    main()