try:
    # prefer CLI if click is available
    from .cli.commands import main as cli_main
except Exception:
    cli_main = None

from .gui.main_window import run as gui_run

if __name__ == "__main__":
    if cli_main is not None:
        cli_main()
    else:
        gui_run()
