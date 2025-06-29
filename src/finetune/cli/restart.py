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

try:
    from typing_extensions import Annotated
except ImportError:
    rprint("❌ [red]typing_extensions is required[/red]")
    sys.exit(1)

from finetune.cli import console, ConfigOption, VerboseOption

def register_restart(app):
    @app.command()
    def restart(
        process_name: Annotated[str, typer.Argument(help="Name of the process to restart")],
        config: ConfigOption = None,
        verbose: VerboseOption = False
    ):
        app_config = Config.load(config) if config else Config()
        manager = SupervisorManager(app_config)

        with console.status(f"[yellow]Restarting {process_name}...", spinner="dots"):
            try:
                manager.restart_process(process_name)
                rprint(f"✅ {process_name} restarted successfully")
            except Exception as e:
                rprint(f"❌ Failed to restart {process_name}: [red]{e}[/red]")
                raise typer.Exit(1)
