import sys
from pathlib import Path

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

from finetune.cli import ConfigOption, VerboseOption

def register_initialize(app):
    @app.command()
    def init(
        config: ConfigOption = None,
        verbose: VerboseOption = False,
        force: Annotated[
            bool,
            typer.Option(
                "--force",
                help="Overwrite existing configuration"
            )
        ] = False
    ):
        config_dir = Path.cwd() / "config"
        config_dir.mkdir(exist_ok=True)

        config_path = config_dir / "supervisord.conf"

        if config_path.exists() and not force:
            rprint(f"⚠️  [yellow]Configuration already exists at {config_path}[/yellow]")
            rprint("Use [cyan]--force[/cyan] to overwrite, or edit the existing file.")
            return

        app_config = Config()
        manager = SupervisorManager(app_config)

        try:
            manager.generate_config(config_path)
            rprint(f"✅ Configuration initialized at [cyan]{config_path}[/cyan]")

            rprint("\n[bold]Next steps:[/bold]")
            rprint("1. [dim]Edit the configuration file to customize your setup[/dim]")
            rprint("2. [dim]Start the application:[/dim] [cyan]finetune start[/cyan]")
            rprint("3. [dim]Check status:[/dim] [cyan]finetune status[/cyan]")

        except Exception as e:
            rprint(f"❌ Failed to initialize configuration: [red]{e}[/red]")
            raise typer.Exit(1)