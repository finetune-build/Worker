import sys

from finetune.supervisor.manager import SupervisorManager
from finetune.config import Config

try:
    from rich import print as rprint
except ImportError:
    rprint("❌ [red]rich is required[/red]")
    sys.exit(1)

try:
    from typing_extensions import Annotated
except ImportError:
    rprint("❌ [red]typing_extensions is required[/red]")
    sys.exit(1)

try:
    import typer
except ImportError:
    rprint("❌ [red]typer is required[/red]")
    sys.exit(1)

from finetune.cli import console, ConfigOption, VerboseOption

def register_start(app):
    @app.command()
    def start(
        config: ConfigOption = None,
        verbose: VerboseOption = False,
        daemon: Annotated[
            bool,
            typer.Option(
                "--daemon", "-d",
                help="Run supervisor in daemon mode"
            )
        ] = True
    ):
        app_config = Config.load(config) if config else Config()
        manager = SupervisorManager(app_config)
    
        with console.status("[green]Starting supervisor processes...", spinner="dots"):
            try:
                manager.start(daemon=daemon)
                rprint("✅  All processes started successfully")
            except Exception as e:
                rprint(f"❌ Failed to start processes: [red]{e}[/red]")
                raise typer.Exit(1)
