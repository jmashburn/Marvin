"""
This module provides a display class for console output.

NOTE: This module appears to be a duplicate or older version of
`marvin.core.display`. It is recommended to use `marvin.core.display.MarvinDisplay`
for console output functionalities.
"""
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress


class MarvinDisplay:
    def __init__(self):
        self.console = Console()
        self.progress = Progress(
            *Progress.get_default_columns(),
            console=self.console,
            expand=True,
            transient=True,
        )

    def print_header(self, tite: str, subtitle: str = None):
        """Print a header message in the console."""
        self.console.print(Panel(f"[bold magenta]{tite}[/bold magenta]\n{subtitle}", expand=False))

    def print_section(self, title: str, subtitle: str = None):
        """Print a section message in the console."""
        self.console.print(f"[bold blue]{title}[/bold blue]")
        if subtitle:
            self.console.print(f"[dim]{subtitle}[/dim]")

    def print_step(self, step: str, title: str, total_steps: int = None, subtitle: str = None):
        """Print a step message in the console."""
        self.console.print(f"[bold green]Step {step}/{total_steps}: {title}[/bold green]")
        if subtitle:
            self.console.print(f"[dim]{subtitle}[/dim]")

    def print_info(self, message: str):
        """Print an info message in the console."""
        self.console.print(f"[bold blue]{message}[/bold blue]")

    def print_success(self, message: str):
        """Print a success message in the console."""
        self.console.print(f"[bold green]{message}[/bold green]")

    def print_warning(self, message: str):
        """Print a warning message in the console."""
        self.console.print(f"[bold yellow]{message}[/bold yellow]")

    def print_error(self, message: str):
        """Print an error message in the console."""
        self.console.print(f"[bold red]{message}[/bold red]")

    def start_spinner(self, message: str):
        """Start a spinner with a message."""
        self.console.print(f"[dim]{message}...[/dim]")
        return self.progress.add_task(message)

    def interactive_prompt(self, message: str, choices: list = None, default: str = None):
        """Display an interactive prompt."""
        prompt = f"{message}"
        if choices:
            prompt += f" ({'/'.join(choices)})"
        if default:
            prompt += f" [default: {default}]"
        self.console.print(f"[bold blue]{message}[/bold blue]")
        return self.console.input(f"{message}: ")
