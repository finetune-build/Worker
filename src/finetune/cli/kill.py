import sys
import subprocess
from finetune.config import Config

try:
    from rich import print as rprint
except ImportError:
    rprint("❌ [red]rich is required[/red]")
    sys.exit(1)

try:
    import typer
except ImportError:
    rprint("❌ [red]typer is required[/red]")
    sys.exit(1)

from finetune.cli import console, ConfigOption, VerboseOption


def register_kill(app):
    @app.command()
    def kill(
        config: ConfigOption = None,
        verbose: VerboseOption = False
    ):
        """
        Force kill all zombie processes.
        
        This command will forcefully kill all supervisord and finetune processes
        that may be stuck or not responding to normal stop commands.
        
        This is a nuclear option - use when normal stop doesn't work.
        """
        app_config = Config.load(config) if config else Config()
        
        # Commands to run
        kill_commands = [
            ("supervisord.*python-sdk", "supervisor processes"),
            ("finetune.processes", "finetune processes")
        ]
        
        killed_any = False
        
        for pattern, description in kill_commands:
            if verbose:
                rprint(f"[yellow]Looking for {description}...[/yellow]")
            
            # First check if there are any processes matching the pattern
            try:
                check_result = subprocess.run(
                    ["pgrep", "-f", pattern],
                    capture_output=True,
                    text=True
                )
                
                if check_result.returncode == 0 and check_result.stdout.strip():
                    # Found processes, count them
                    pids = check_result.stdout.strip().split('\n')
                    count = len(pids)
                    
                    if verbose:
                        rprint(f"[yellow]Found {count} {description}[/yellow]")
                        for pid in pids:
                            rprint(f"  • PID {pid}")
                    
                    # Kill them
                    with console.status(f"[red]Killing {description}...", spinner="dots"):
                        try:
                            kill_result = subprocess.run(
                                ["pkill", "-f", pattern],
                                capture_output=True,
                                text=True
                            )
                            
                            if kill_result.returncode == 0:
                                rprint(f"[green]✓[/green] Killed {count} {description}")
                                killed_any = True
                            else:
                                rprint(f"[yellow]⚠[/yellow] No {description} found or already killed")
                                
                        except Exception as e:
                            rprint(f"[red]✗[/red] Failed to kill {description}: {e}")
                            
                else:
                    if verbose:
                        rprint(f"[dim]No {description} found[/dim]")
                    
            except Exception as e:
                if verbose:
                    rprint(f"[yellow]⚠[/yellow] Error checking for {description}: {e}")
        
        # Clean up socket files
        socket_files = [
            "/tmp/finetune/supervisor.sock",
            "/tmp/finetune/supervisord.pid"
        ]
        
        cleaned_files = []
        for socket_file in socket_files:
            try:
                import os
                if os.path.exists(socket_file):
                    os.unlink(socket_file)
                    cleaned_files.append(socket_file)
                    if verbose:
                        rprint(f"[green]🧹[/green] Removed {socket_file}")
            except Exception as e:
                if verbose:
                    rprint(f"[yellow]⚠[/yellow] Could not remove {socket_file}: {e}")
        
        # Summary
        if killed_any:
            rprint("[green]✓[/green] Zombie processes killed successfully")
        else:
            rprint("[green]✓[/green] No zombie processes found")
        
        if cleaned_files and verbose:
            rprint(f"[green]🧹[/green] Cleaned up {len(cleaned_files)} socket files")
        
        if not verbose and killed_any:
            rprint("[dim]Use --verbose to see detailed information[/dim]")