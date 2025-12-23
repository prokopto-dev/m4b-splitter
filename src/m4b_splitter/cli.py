# ruff: noqa: B008
"""Command-line interface for M4B splitter."""
# we will ignore Ruff B008 here because of how Typer handles args

import sys
from enum import Enum
from pathlib import Path

# Try to import typer and rich, fall back to basic CLI if not available
try:
    import typer
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    typer = None  # type: ignore

from m4b_splitter import (
    IPOD_PRESETS,
    FFmpegProgress,
    M4BSplitter,
    format_time_human,
)
from m4b_splitter.dependencies import check_dependencies, format_dependency_check


def parse_duration(duration_str: str) -> float:
    """Parse a duration string into hours."""
    duration_str = duration_str.strip().lower()

    try:
        return float(duration_str)
    except ValueError:
        pass

    if duration_str.endswith("h") and "m" not in duration_str:
        try:
            return float(duration_str[:-1])
        except ValueError:
            pass

    if duration_str.endswith("m") and "h" not in duration_str:
        try:
            return float(duration_str[:-1]) / 60
        except ValueError:
            pass

    if "h" in duration_str and "m" in duration_str:
        try:
            parts = duration_str.replace("m", "").split("h")
            hours = float(parts[0])
            minutes = float(parts[1]) if parts[1] else 0
            return hours + minutes / 60
        except (ValueError, IndexError):
            pass

    raise ValueError(f"Invalid duration format: {duration_str}")


# ============================================================================
# Rich/Typer CLI (when dependencies are available)
# ============================================================================

if RICH_AVAILABLE:

    class PresetChoice(str, Enum):
        standard = "standard"
        high = "high"
        extended = "extended"
        video = "video"

    app = typer.Typer(
        name="m4b-splitter",
        help="Split M4B audiobook files by chapter at specified duration limits.",
        add_completion=False,
        rich_markup_mode="rich",
    )

    console = Console()

    def print_presets_table():
        table = Table(title="iPod Encoding Presets", show_header=True, header_style="bold cyan")
        table.add_column("Preset", style="green")
        table.add_column("Sample Rate")
        table.add_column("Bitrate")
        table.add_column("Channels")
        table.add_column("Mode")
        table.add_column("Max Duration", style="yellow")
        table.add_column("Best For")

        preset_info = {
            "standard": (
                "22050 Hz",
                "64 kbps",
                "Mono",
                "VBR",
                "~55h",
                "Most audiobooks",
            ),
            "high": (
                "44100 Hz",
                "128 kbps",
                "Stereo",
                "VBR",
                "~27h",
                "Music/High quality",
            ),
            "extended": (
                "16000 Hz",
                "48 kbps",
                "Mono",
                "VBR",
                "~74h",
                "Very long books",
            ),
            "video": (
                "44100 Hz",
                "80 kbps",
                "Mono",
                "CBR",
                "~27h",
                "iPod Video (5th Gen)",
            ),
        }

        for name, info in preset_info.items():
            table.add_row(name, *info)

        console.print(table)

    @app.command()
    def check():
        """Check if ffmpeg/ffprobe are installed."""
        result = check_dependencies()

        if result.all_found:
            content = Text()
            content.append("✓ ", style="green bold")
            content.append("All dependencies found!\n\n", style="green")
            content.append(f"OS: {result.os_name}\n\n", style="dim")
            content.append(f"ffmpeg:  {result.ffmpeg.path}\n", style="cyan")
            content.append(f"ffprobe: {result.ffprobe.path}\n", style="cyan")
            console.print(Panel(content, title="Dependency Check", border_style="green"))
        else:
            console.print(format_dependency_check(result))
            raise typer.Exit(1)

    @app.command()
    def presets():
        """Show available iPod encoding presets."""
        print_presets_table()

    @app.command()
    def split(
        input_file: Path = typer.Argument(..., help="Input M4B file to split", exists=True),
        output_dir: Path = typer.Option(None, "--output", "-o", help="Output directory"),
        max_duration: str = typer.Option("8h", "--duration", "-d", help="Max duration per part"),
        pattern: str = typer.Option("{title} - Part {part} of {total}.m4b", "--pattern", "-p"),
        ipod: bool = typer.Option(False, "--ipod", help="Re-encode for iPod compatibility"),
        ipod_preset: PresetChoice = typer.Option(PresetChoice.standard, "--preset"),
    ):
        """Split an M4B audiobook file into smaller parts."""
        dep_result = check_dependencies()
        if not dep_result.all_found:
            console.print("[red]Error:[/red] ffmpeg/ffprobe not found!")
            console.print(format_dependency_check(dep_result))
            raise typer.Exit(1)

        try:
            max_hours = parse_duration(max_duration)
            if max_hours <= 0:
                console.print("[red]Error:[/red] Duration must be positive")
                raise typer.Exit(1)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from e

        if output_dir is None:
            output_dir = input_file.parent

        ipod_settings = IPOD_PRESETS.get(ipod_preset.value) if ipod else None

        # Configuration display
        config_text = Text()
        config_text.append("Input:        ", style="dim")
        config_text.append(f"{input_file.name}\n", style="cyan")
        config_text.append("Output Dir:   ", style="dim")
        config_text.append(f"{output_dir}\n", style="cyan")
        config_text.append("Max Duration: ", style="dim")
        config_text.append(
            f"{max_hours:.2f} hours ({format_time_human(max_hours * 3600)})\n",
            style="yellow",
        )

        if ipod and ipod_settings:
            config_text.append("iPod Mode:    ", style="dim")
            config_text.append("Enabled\n", style="green")
            config_text.append("Preset:       ", style="dim")
            config_text.append(f"{ipod_preset.value}\n", style="green")
            config_text.append("Encoding:     ", style="dim")
            config_text.append(
                f"{ipod_settings.sample_rate}Hz, {ipod_settings.bitrate}kbps, "
                f"{'mono' if ipod_settings.channels == 1 else 'stereo'}"
                f"{', CBR' if ipod_settings.use_cbr else ''}\n",
                style="cyan",
            )
        else:
            config_text.append("iPod Mode:    ", style="dim")
            config_text.append("Disabled (stream copy)\n", style="dim")

        console.print(Panel(config_text, title="Configuration", border_style="blue"))
        console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=False,
        ) as progress:
            main_task = progress.add_task("Splitting audiobook...", total=100)
            ffmpeg_task = progress.add_task("[cyan]Waiting...", total=100, visible=False)

            def progress_callback(step: str, percent: float, ffmpeg_prog: FFmpegProgress | None):
                progress.update(main_task, completed=percent, description=f"[bold blue]{step}")

                if ffmpeg_prog and ffmpeg_prog.percent > 0:
                    progress.update(ffmpeg_task, visible=True)
                    details = []
                    if ffmpeg_prog.speed > 0:
                        details.append(f"{ffmpeg_prog.speed:.1f}x")
                    if ffmpeg_prog.bitrate_kbps > 0:
                        details.append(f"{ffmpeg_prog.bitrate_kbps:.0f}kbps")
                    if ffmpeg_prog.size_kb > 0:
                        details.append(f"{ffmpeg_prog.size_kb / 1024:.1f}MB")

                    detail_str = " | ".join(details) if details else ""
                    time_str = format_time_human(ffmpeg_prog.time_seconds)

                    progress.update(
                        ffmpeg_task,
                        completed=ffmpeg_prog.percent,
                        description=f"[cyan]  └─ {time_str} encoded {detail_str}",
                    )
                elif "Processing" not in step and "Encoding" not in step:
                    progress.update(ffmpeg_task, visible=False)

            splitter = M4BSplitter()
            result = splitter.split(
                input_file=input_file,
                output_dir=output_dir,
                max_duration_hours=max_hours,
                output_pattern=pattern,
                ipod_mode=ipod,
                ipod_preset=ipod_preset.value,
                progress_callback=progress_callback,
            )

            progress.update(ffmpeg_task, visible=False)
            progress.update(main_task, completed=100)

        console.print()

        if result.success:
            if result.parts:
                result_table = Table(
                    title="✓ Split Complete",
                    show_header=True,
                    header_style="bold green",
                )
                result_table.add_column("Part", style="cyan", justify="center")
                result_table.add_column("Duration", justify="right")
                result_table.add_column("Chapters", justify="center")
                result_table.add_column("File")

                for part in result.parts:
                    result_table.add_row(
                        f"{part.part_number}/{part.total_parts}",
                        format_time_human(part.duration),
                        str(len(part.chapters)),
                        part.output_path.name,
                    )

                console.print(result_table)
                console.print()
                console.print("[bold]Output files:[/bold]")
                for path in result.output_files:
                    console.print(f"  [green]✓[/green] {path}")
            else:
                console.print(
                    Panel(
                        f"[yellow]No split needed[/yellow] - file already under {max_hours:.1f} hours",
                        border_style="yellow",
                    )
                )
        else:
            console.print(
                Panel(
                    f"[red bold]Error:[/red bold] {result.error_message}",
                    title="Split Failed",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

    @app.callback(invoke_without_command=True)
    def main_callback(
        ctx: typer.Context,
        version: bool = typer.Option(False, "--version", "-v", help="Show version"),
    ):
        """M4B Splitter - Split audiobook files by chapter."""
        if version:
            from m4b_splitter import __version__

            console.print(f"m4b-splitter version {__version__}")
            raise typer.Exit()

        if ctx.invoked_subcommand is None:
            console.print(ctx.get_help())


# ============================================================================
# Fallback CLI (when typer/rich not available)
# ============================================================================

else:
    import argparse

    def fallback_main() -> int:
        """Fallback CLI using argparse."""
        parser = argparse.ArgumentParser(
            prog="m4b-splitter", description="Split M4B audiobook files by chapter."
        )

        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("check", help="Check ffmpeg installation")
        subparsers.add_parser("presets", help="Show iPod presets")

        split_parser = subparsers.add_parser("split", help="Split an M4B file")
        split_parser.add_argument("input_file", type=Path, help="Input M4B file")
        split_parser.add_argument("-o", "--output", type=Path, help="Output directory")
        split_parser.add_argument("-d", "--duration", default="8h")
        split_parser.add_argument("-p", "--pattern", default="{title} - Part {part} of {total}.m4b")
        split_parser.add_argument("--ipod", action="store_true")
        split_parser.add_argument("--preset", default="standard", choices=list(IPOD_PRESETS.keys()))

        parser.add_argument("-v", "--version", action="store_true")

        args = parser.parse_args()

        if args.version:
            from m4b_splitter import __version__

            print(f"m4b-splitter version {__version__}")
            return 0

        if args.command == "check":
            result = check_dependencies()
            print(format_dependency_check(result))
            return 0 if result.all_found else 1

        elif args.command == "presets":
            print("\niPod Encoding Presets:")
            for name, settings in IPOD_PRESETS.items():
                print(f"  {name}: {settings}")
            return 0

        elif args.command == "split":
            dep_result = check_dependencies()
            if not dep_result.all_found:
                print("Error: ffmpeg/ffprobe not found!")
                return 1

            try:
                max_hours = parse_duration(args.duration)
            except ValueError as e:
                print(f"Error: {e}")
                return 1

            output_dir = args.output or args.input_file.parent

            print(f"\nSplitting: {args.input_file}")
            print(f"Output:    {output_dir}")
            print(f"Max:       {max_hours:.2f} hours")
            if args.ipod:
                print(f"iPod:      {args.preset}")

            def progress_cb(step: str, percent: float, _: FFmpegProgress | None):
                bar = "=" * int(percent / 2) + " " * (50 - int(percent / 2))
                print(f"\r[{bar}] {percent:5.1f}% {step}", end="", flush=True)

            splitter = M4BSplitter()
            result = splitter.split(
                input_file=args.input_file,
                output_dir=output_dir,
                max_duration_hours=max_hours,
                output_pattern=args.pattern,
                ipod_mode=args.ipod,
                ipod_preset=args.preset,
                progress_callback=progress_cb,
            )

            print("\n")

            if result.success:
                if result.parts:
                    print(f"Success! Created {len(result.parts)} parts:")
                    for part in result.parts:
                        print(f"  Part {part.part_number}: {part.output_path}")
                else:
                    print("No split needed")
                return 0
            else:
                print(f"Error: {result.error_message}")
                return 1

        else:
            parser.print_help()
            return 0

    def app():
        sys.exit(fallback_main())


def main():
    if RICH_AVAILABLE:
        app()
    else:
        sys.exit(fallback_main())


if __name__ == "__main__":
    main()
