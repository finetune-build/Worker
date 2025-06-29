import sys
from pathlib import Path

from finetune.supervisor.manager import SupervisorManager
from finetune.config import Config

try:
    from rich import print as rprint
except ImportError:
    rprint("❌ [red]rich is required[/red]")
    sys.exit(1)

from finetune.cli import ConfigOption, VerboseOption

def register_health(app):
    @app.command()
    def health(
        config: ConfigOption = None,
        verbose: VerboseOption = False
    ):
        app_config = Config.load(config) if config else Config()
        manager = SupervisorManager(app_config)

        rprint("[bold]🩺 Health Check Results[/bold]")
        rprint("=" * 50)

        try:
            status_info = manager.get_status()
            if status_info:
                rprint("✅ Supervisor daemon: [green]Running[/green]")
                running_count = sum(1 for info in status_info.values()
                                    if info.get('statename') == 'RUNNING')
                total_count = len(status_info)
                rprint(f"✅ Processes: [green]{running_count}/{total_count} running[/green]")
            else:
                rprint("⚠️  Supervisor daemon: [yellow]Not running[/yellow]")
        except Exception as e:
            rprint(f"❌ Supervisor daemon: [red]Error - {e}[/red]")

        try:
            config_path = Path.cwd() / "config" / "supervisord.conf"
            if config_path.exists():
                rprint(f"✅ Configuration: [green]Found at {config_path}[/green]")
            else:
                rprint("⚠️  Configuration: [yellow]Not found (run 'init' command)[/yellow]")
        except Exception as e:
            rprint(f"❌ Configuration: [red]Error - {e}[/red]")