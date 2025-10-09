"""
CLI command for generating TypeScript interfaces from Pydantic models.
"""

import click
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from computor_backend.scripts.generate_typescript_interfaces import TypeScriptGenerator


@click.command()
@click.option(
    '--output-dir',
    '-o',
    type=click.Path(path_type=Path),
    help='Output directory for TypeScript files (default: frontend/src/types/generated)'
)
@click.option(
    '--watch',
    '-w',
    is_flag=True,
    help='Watch for changes and regenerate automatically'
)
@click.option(
    '--clean',
    is_flag=True,
    help='Clean output directory before generating'
)
@click.option(
    '--include-timestamps/--no-include-timestamps',
    default=False,
    help='Include "Generated on" timestamps in file headers'
)
def generate_types(output_dir: Path = None, watch: bool = False, clean: bool = False, include_timestamps: bool = False):
    """Generate TypeScript interfaces from Pydantic models."""
    
    # Determine paths
    cli_dir = Path(__file__).parent  # computor_cli
    cli_src_dir = cli_dir.parent  # src (computor-cli/src)
    cli_root = cli_src_dir.parent  # computor-cli
    project_root = cli_root.parent  # computor-fullstack
    backend_root = project_root / "computor-backend"
    types_package = project_root / "computor-types" / "src" / "computor_types"

    # Default output directory
    if output_dir is None:
        output_dir = project_root / "generated" / "types"

    # Directories to scan for models - use computor-types package
    scan_dirs = [
        types_package,  # All Pydantic DTOs are in computor-types
    ]
    
    click.echo(click.style("🚀 TypeScript Interface Generator", fg='green', bold=True))
    click.echo("=" * 50)
    
    # Clean output directory if requested
    if clean and output_dir.exists():
        click.echo(f"🧹 Cleaning output directory: {output_dir}")
        import shutil
        shutil.rmtree(output_dir)
    
    # Generate interfaces
    generator = TypeScriptGenerator(include_timestamp=include_timestamps)
    
    def run_generation():
        click.echo(f"📂 Scanning directories:")
        for scan_dir in scan_dirs:
            click.echo(f"  - {scan_dir}")
        click.echo(f"📁 Output directory: {output_dir}")
        click.echo("=" * 50)
        
        generated_files = generator.generate_all(scan_dirs, output_dir)
        
        click.echo("=" * 50)
        click.echo(click.style(f"✅ Generated {len(generated_files)} TypeScript files", fg='green'))
        return generated_files
    
    # Initial generation
    generated_files = run_generation()
    
    # Watch mode
    if watch:
        click.echo("\n👀 Watching for changes... (Press Ctrl+C to stop)")
        
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class ModelChangeHandler(FileSystemEventHandler):
                def on_modified(self, event):
                    if event.is_directory:
                        return
                    
                    if event.src_path.endswith('.py'):
                        # Check if it's in one of our scan directories
                        for scan_dir in scan_dirs:
                            if str(scan_dir) in event.src_path:
                                click.echo(f"\n🔄 Detected change in {event.src_path}")
                                run_generation()
                                click.echo("👀 Watching for changes...")
                                break
            
            event_handler = ModelChangeHandler()
            observer = Observer()
            
            for scan_dir in scan_dirs:
                observer.schedule(event_handler, str(scan_dir), recursive=True)
            
            observer.start()
            
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
                click.echo("\n👋 Stopped watching")
            
            observer.join()
            
        except ImportError:
            click.echo(click.style(
                "\n⚠️  Watch mode requires 'watchdog' package. Install with: pip install watchdog",
                fg='yellow'
            ))
    
    click.echo("\n🎯 You can now use these interfaces in your React app!")


if __name__ == '__main__':
    generate_types()
