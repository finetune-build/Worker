import sys

from finetune.supervisor.manager import SupervisorManager
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

from finetune.cli import ConfigOption, VerboseOption

def register_stop(app):
    @app.command()
    def stop(
        config: ConfigOption = None,
        verbose: VerboseOption = False
    ):
        """
        Stop all processes.

        This command will gracefully stop all running processes
        and shutdown the supervisor daemon.
        """
        app_config = Config.load(config) if config else Config()
        manager = SupervisorManager(app_config)

        # First check if there are any processes running
        try:
            status_info = manager.get_status()

            if not status_info:
                rprint("[yellow]ℹ[/yellow] No supervisor processes found to stop")
                return

            # Check if any processes are actually running
            running_processes = [
                name for name, info in status_info.items() 
                if info.get('statename') == 'RUNNING'
            ]

            if not running_processes:
                rprint("[yellow]ℹ[/yellow] No processes are currently running")
                # Still try to shutdown supervisor daemon if it's running
                try:
                    manager.stop()
                    rprint("[green]✓[/green] Supervisor daemon stopped")
                except Exception:
                    rprint("[dim]Supervisor daemon was not running[/dim]")
                return

            # Show which processes will be stopped
            rprint(f"[yellow]Stopping {len(running_processes)} running process(es):[/yellow]")
            for proc_name in running_processes:
                rprint(f"  • {proc_name}")

        except Exception as e:
            # If we can't get status, supervisor might not be running
            rprint("[yellow]ℹ[/yellow] Supervisor daemon does not appear to be running")
            return

        # Proceed with stopping if we have running processes
        with console.status("[yellow]Stopping all processes...", spinner="dots"):
            try:
                manager.stop()
                rprint("[green]✓[/green] All processes stopped successfully")
            except Exception as e:
                # Check if it's just a "no processes to stop" type error
                error_msg = str(e).lower()
                if any(phrase in error_msg for phrase in [
                    "refused connection", 
                    "no such file", 
                    "connection refused",
                    "not running"
                ]):
                    rprint("[yellow]ℹ[/yellow] Supervisor was not running")
                else:
                    rprint(f"[red]✗[/red] Failed to stop processes: {e}")
                    raise typer.Exit(1)