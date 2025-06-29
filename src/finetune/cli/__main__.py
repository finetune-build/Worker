import sys
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
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

app = typer.Typer(
    name="finetune",
    help="finetune.build sdk tools",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()

ConfigOption = Annotated[
    Optional[Path],
    typer.Option(
        "--config", "-c",
        help="Path to configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True
    )
]

VerboseOption = Annotated[
    bool,
    typer.Option(
        "--verbose", "-v",
        help="Enable verbose logging"
    )
]

def _rich_exception_handler(exc_type, exc_value, exc_traceback):
    """Handle exceptions with rich formatting."""
    if exc_type is KeyboardInterrupt:
        rprint("\n ⚠️  [yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    else:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = _rich_exception_handler
