# finetune/utils/redis_health.py

import subprocess
import time
import platform
import sys

import redis
import typer
from redis.exceptions import ConnectionError, RedisError
from rich import print as rprint

from finetune.config import RedisConfig


class RedisHealthChecker:
    """Check Redis health and optionally start Redis if needed."""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.system = platform.system().lower()
    
    def prompt_redis_installation(self) -> bool:
        """Ask user if they want to install Redis."""
        if not sys.stdin.isatty():  # Skip prompt in non-interactive environments
            return False
        
        response = typer.confirm(
            "Redis is not available. Would you like to install it now?",
            default=True
        )
        return response
    
    def _has_homebrew(self) -> bool:
        """Check if Homebrew is installed on macOS."""
        try:
            result = subprocess.run(['brew', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _install_via_homebrew(self) -> bool:
        """Install Redis via Homebrew on macOS."""
        try:
            rprint("[cyan]📦 Installing Redis via Homebrew...[/cyan]")
            result = subprocess.run(['brew', 'install', 'redis'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                rprint("[green]✅ Redis installed successfully[/green]")
                return True
            else:
                rprint(f"[red]❌ Homebrew install failed: {result.stderr}[/red]")
                return False
        except Exception as e:
            rprint(f"[red]❌ Error installing via Homebrew: {e}[/red]")
            return False
    
    def _install_via_apt_or_yum(self) -> bool:
        """Install Redis via apt or yum on Linux."""
        # Try apt first (Debian/Ubuntu)
        try:
            rprint("[cyan]📦 Installing Redis via apt...[/cyan]")
            result = subprocess.run(['sudo', 'apt-get', 'update'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                result = subprocess.run(['sudo', 'apt-get', 'install', '-y', 'redis-server'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    rprint("[green]✅ Redis installed successfully via apt[/green]")
                    return True
        except Exception:
            pass
        
        # Try yum (RHEL/CentOS/Fedora)
        try:
            rprint("[cyan]📦 Installing Redis via yum...[/cyan]")
            result = subprocess.run(['sudo', 'yum', 'install', '-y', 'redis'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                rprint("[green]✅ Redis installed successfully via yum[/green]")
                return True
        except Exception:
            pass
        
        # Try dnf (newer Fedora)
        try:
            rprint("[cyan]📦 Installing Redis via dnf...[/cyan]")
            result = subprocess.run(['sudo', 'dnf', 'install', '-y', 'redis'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                rprint("[green]✅ Redis installed successfully via dnf[/green]")
                return True
        except Exception:
            pass
        
        rprint("[red]❌ Could not install Redis via package manager[/red]")
        return False
    
    def install_redis(self) -> bool:
        """Install Redis using system package manager."""
        try:
            if self.system == 'darwin':  # macOS
                # Check if Homebrew is installed first
                if self._has_homebrew():
                    return self._install_via_homebrew()
                else:
                    rprint("[yellow]⚠️  Homebrew not found. Please install Homebrew first.[/yellow]")
                    rprint("Visit: https://brew.sh")
                    return False

            elif self.system == 'linux':
                return self._install_via_apt_or_yum()

            elif self.system == 'windows':
                rprint("[yellow]⚠️  Automatic Redis installation on Windows not supported.[/yellow]")
                rprint("Please use WSL or download from: https://redis.io/downloads/")
                return False

        except Exception as e:
            rprint(f"[red]❌ Installation failed: {e}[/red]")
            return False
    
    def check_redis_connection(self, timeout: int = 5) -> bool:
        """Check if Redis is accessible."""
        try:
            client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                socket_connect_timeout=timeout,
                socket_timeout=timeout
            )
            client.ping()
            return True
        except (ConnectionError, RedisError, Exception):
            return False
    
    def is_redis_running(self) -> bool:
        """Check if Redis server process is running."""
        try:
            if self.system in ['darwin', 'linux']:  # macOS or Linux
                # Check if redis-server is running
                result = subprocess.run(
                    ['pgrep', '-f', 'redis-server'],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            elif self.system == 'windows':
                # Check Windows Redis service
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq redis-server.exe'],
                    capture_output=True,
                    text=True
                )
                return 'redis-server.exe' in result.stdout
            return False
        except Exception:
            return False
    
    def start_redis(self) -> bool:
        """Attempt to start Redis server."""
        if self.is_redis_running():
            return True
        
        try:
            if self.system == 'darwin':  # macOS
                # Try Homebrew Redis
                result = subprocess.run(
                    ['brew', 'services', 'start', 'redis'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    rprint("[green]✅ Started Redis via Homebrew[/green]")
                    return self._wait_for_redis()
                
                # Try direct redis-server
                subprocess.Popen(['redis-server'], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                rprint("[green]✅ Started Redis server directly[/green]")
                return self._wait_for_redis()
                
            elif self.system == 'linux':
                # Try systemctl (Ubuntu/Debian/CentOS)
                for service_name in ['redis-server', 'redis']:
                    result = subprocess.run(
                        ['sudo', 'systemctl', 'start', service_name],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        rprint(f"[green]✅ Started Redis via systemctl ({service_name})[/green]")
                        return self._wait_for_redis()
                
                # Try direct redis-server
                subprocess.Popen(['redis-server'], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                rprint("[green]✅ Started Redis server directly[/green]")
                return self._wait_for_redis()
                
            elif self.system == 'windows':
                # Try Windows service
                result = subprocess.run(
                    ['net', 'start', 'Redis'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    rprint("[green]✅ Started Redis Windows service[/green]")
                    return self._wait_for_redis()
                
        except Exception as e:
            rprint(f"[yellow]⚠️  Could not auto-start Redis: {e}[/yellow]")
            return False
        
        return False
    
    def _wait_for_redis(self, max_wait: int = 10) -> bool:
        """Wait for Redis to become available."""
        for i in range(max_wait):
            if self.check_redis_connection():
                return True
            time.sleep(1)
        return False
    
    def ensure_redis_available(self, auto_start: bool = True, allow_install: bool = True) -> bool:
        """Ensure Redis is available, optionally starting it."""
        # Check if already connected
        if self.check_redis_connection():
            rprint("[green]✅ Redis is running and accessible[/green]")
            return True
        
        # Check if Redis process is running but not responding
        if self.is_redis_running():
            rprint("[yellow]⚠️  Redis process running but not responding[/yellow]")
            time.sleep(2)  # Give it a moment
            if self.check_redis_connection():
                return True
        
        # Try to start Redis if requested
        if auto_start:
            rprint("[yellow]🔄 Redis not running, attempting to start...[/yellow]")
            if self.start_redis():
                rprint("[green]✅ Redis started successfully[/green]")
                return True
        
        # Ask to install Redis if not available and installation is allowed
        if allow_install and self.prompt_redis_installation():
            if self.install_redis():
                # After installation, try to start Redis
                if self.start_redis():
                    rprint("[green]✅ Redis installed and started successfully[/green]")
                    return True
                else:
                    rprint("[yellow]⚠️  Redis installed but failed to start automatically[/yellow]")
                    return self.ensure_redis_available(auto_start=True, allow_install=False)
        
        # Redis is not available
        rprint("[red]❌ Redis is not available[/red]")
        return False
    
    def show_redis_help(self):
        """Show help for manually starting Redis."""
        rprint("\n[yellow]💡 To start Redis manually:[/yellow]")
        
        if self.system == 'darwin':  # macOS
            rprint("  • [cyan]brew install redis[/cyan] (if not installed)")
            rprint("  • [cyan]brew services start redis[/cyan]")
            rprint("  • Or: [cyan]redis-server[/cyan]")
        elif self.system == 'linux':
            rprint("  • [cyan]sudo apt-get install redis-server[/cyan] (Ubuntu/Debian)")
            rprint("  • [cyan]sudo systemctl start redis-server[/cyan]")
            rprint("  • Or: [cyan]redis-server[/cyan]")
        elif self.system == 'windows':
            rprint("  • Download Redis from: https://redis.io/downloads/")
            rprint("  • Or use WSL: [cyan]wsl -e sudo service redis-server start[/cyan]")
        
        rprint(f"  • Check connection: [cyan]redis-cli ping[/cyan]")
        rprint(f"  • Expected response: [green]PONG[/green]")


def check_redis_before_start(app_config, detach=False):
    """Check Redis availability before starting processes."""
    redis_checker = RedisHealthChecker(app_config.redis)
    
    if not redis_checker.ensure_redis_available(auto_start=True, allow_install=not detach):
        if not detach:  # Only show detailed help in non-detached mode
            rprint("\n[red]❌ Cannot start processes without Redis[/red]")
            redis_checker.show_redis_help()
            rprint("\n[yellow]Try running one of the above commands, then run:[/yellow]")
            rprint("  [cyan]finetune start[/cyan]")
        raise typer.Exit(1)