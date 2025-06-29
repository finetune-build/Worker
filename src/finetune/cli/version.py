import sys
import importlib.metadata

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

def register_version(app):
    @app.command()
    def version() -> None:
        """Show the finetune-sdk version."""
        try:
            version = importlib.metadata.version("finetune-sdk")
            rprint(f"✅ finetune-sdk version {version}")
        except importlib.metadata.PackageNotFoundError:
            rprint("⚠️  [yellow]finetune-sdk version unknown (package not installed)[/yellow]")
            typer.Exit()
