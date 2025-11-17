from typing import Optional, Callable, Any

# prefer CLI if click is available
cli_main: Optional[Callable[[], Any]] = None
try:
    from .cli.commands import main as cli_main
except Exception:
    cli_main = None

from .gui.main_window import run as gui_run

if __name__ == "__main__":
    if cli_main is not None:
        cli_main()
    else:
        gui_run()
