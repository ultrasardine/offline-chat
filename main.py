"""Entry point for the Offline Chat application."""

from offline_chat.cli import CLI


def main():
    """Start the Offline Chat CLI application."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
