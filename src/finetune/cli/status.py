import sys

from finetune.supervisor.manager import SupervisorManager
from finetune.config import Config

try:
    from rich.table import Table
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

def register_status(app):
    @app.command()
    def status(
        config: ConfigOption = None,
        verbose: VerboseOption = False
    ):
        app_config = Config.load(config) if config else Config()
        manager = SupervisorManager(app_config)

        try:
            status_info = manager.get_status()

            if not status_info:
                rprint("[yellow]⚠️  No processes found. Start the app first with:[/yellow] [cyan]finetune start[/cyan]")
                return

            table = Table(title="Process Status", show_header=True, header_style="bold cyan")
            table.add_column("Process Name", style="white", width=20)
            table.add_column("Status", width=12)
            table.add_column("PID", style="dim", width=10)
            table.add_column("Description", style="dim")

            for process_name, info in status_info.items():
                state = info.get('statename', 'UNKNOWN')
                pid = str(info.get('pid', 'N/A'))
                description = info.get('description', '')

                if state == 'RUNNING':
                    status_style = "[green]"
                elif state in ['STOPPED', 'EXITED']:
                    status_style = "[yellow]"
                else:
                    status_style = "[red]"

                table.add_row(
                    process_name,
                    f"{status_style}{state}[/]",
                    pid,
                    description
                )

            console.print(table)

        except Exception as e:
            rprint(f"❌ Failed to get status: [red]{e}[/red]")
            raise typer.Exit(1)
