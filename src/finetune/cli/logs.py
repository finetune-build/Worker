import sys

from typing import Optional

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

def register_logs(app):
    @app.command()
    def logs(
        config: ConfigOption = None,
        verbose: VerboseOption = False,
        follow: Annotated[
            bool,
            typer.Option(
                "--follow", "-f",
                help="Follow log output (tail -f style)"
            )
        ] = False,
        process: Annotated[
            Optional[str],
            typer.Option(
                "--process", "-p",
                help="Show logs for specific process only"
            )
        ] = None
    ):
        app_config = Config.load(config) if config else Config()
        manager = SupervisorManager(app_config)

        try:
            if follow:
                rprint(f"[dim]📜 Following logs{' for ' + process if process else ''}... (Press Ctrl+C to stop)[/dim]")

            manager.show_logs(process_name=process, follow=follow)

        except KeyboardInterrupt:
            rprint("\n ⚠️  [yellow]Log following stopped[/yellow]")
        except Exception as e:
            rprint(f"❌ Failed to show logs: [red]{e}[/red]")
            raise typer.Exit(1)
