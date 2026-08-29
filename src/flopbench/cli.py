"""Stage 0 command-line entry point."""

from typing import Annotated

import typer

from flopbench import __version__

app = typer.Typer(
    add_completion=False,
    help="Unofficial, independent, local-first FlopBench community workbench.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print the package version and exit."""
    if value:
        typer.echo(f"flopbench {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = None,
) -> None:
    """FlopBench is unofficial and does not provide FLOP eligibility or rewards."""
