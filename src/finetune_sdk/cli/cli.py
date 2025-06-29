import sys
import importlib.metadata

try:
    import typer
except ImportError:
    print("Error: typer is required")
    sys.exit(1)

try:
    import dotenv
except ImportError:
    dotenv = None

app = typer.Typer(
    name="finetune",
    help="finetune.build sdk tools",
    add_completion=False,
    no_args_is_help=True,  # Show help if no args provided
)

@app.command()
def version() -> None:
    """Show the finetune-sdk version."""
    try:
        version = importlib.metadata.version("finetune-sdk")
        print(f"finetune-sdk version {version}")
    except importlib.metadata.PackageNotFoundError:
        print("finetune-sdk version unknown (package not installed)")
        sys.exit(1)

@app.command()
def dev() -> None:
    print("TODO: Add development environment.")


@app.command()
def run() -> None:
    print("TODO: Add run command.")
