"""
Computor Framework - Blocks CLI

Command-line interface for exporting test block definitions
to JSON Schema and TypeScript for use in VSCode extensions.
"""

import json
import click
from pathlib import Path

from .models import (
    get_all_blocks,
    get_language_blocks,
    export_json_schema,
    export_test_yaml_schema,
    export_typescript,
    export_field_visibility,
    generate_test_yaml,
    generate_full_test_yaml,
    get_templates,
    get_templates_by_test_type,
    export_templates_json,
)


@click.group()
@click.version_option(version="0.1.0", prog_name="blocks")
def cli():
    """Computor Framework - Test Blocks Export Tool

    Export test block definitions to JSON Schema and TypeScript
    for integration with VSCode extensions.
    """
    pass


@cli.command()
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output file path (prints to stdout if not specified)"
)
@click.option(
    "-l", "--language",
    type=click.Choice(["python", "c", "octave", "r", "julia", "fortran", "document", "all"], case_sensitive=False),
    default="all",
    help="Language to export (default: all)"
)
def schema(output, language):
    """Export JSON Schema for test blocks.

    Examples:

        blocks schema                    # Print all to stdout
        blocks schema -o blocks.json     # Write to file
        blocks schema -l python          # Only Python blocks
    """
    if language == "all":
        json_str = export_json_schema()
    else:
        blocks = get_language_blocks(language)
        schema_data = blocks.model_json_schema()
        schema_data["$schema"] = "http://json-schema.org/draft-07/schema#"
        schema_data["title"] = f"Computor - {blocks.name} Blocks"
        json_str = json.dumps(schema_data, indent=2)

    if output:
        Path(output).write_text(json_str)
        click.echo(f"JSON Schema written to: {output}")
    else:
        click.echo(json_str)


@cli.command()
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output file path (prints to stdout if not specified)"
)
def typescript(output):
    """Export TypeScript interfaces for test blocks.

    Examples:

        blocks typescript                    # Print to stdout
        blocks typescript -o types.ts        # Write to file
    """
    ts_code = export_typescript()

    if output:
        Path(output).write_text(ts_code)
        click.echo(f"TypeScript interfaces written to: {output}")
    else:
        click.echo(ts_code)


@cli.command()
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output file path (prints to stdout if not specified)"
)
@click.option(
    "-l", "--language",
    type=click.Choice(["python", "c", "octave", "r", "julia", "fortran", "document", "all"], case_sensitive=False),
    default="all",
    help="Language to export (default: all)"
)
def data(output, language):
    """Export raw block data as JSON.

    This exports the actual block definitions (not the schema)
    which can be used directly by applications.

    Examples:

        blocks data                      # Print all blocks
        blocks data -o blocks-data.json  # Write to file
        blocks data -l c                 # Only C/C++ blocks
    """
    if language == "all":
        blocks = get_all_blocks()
        data_dict = blocks.model_dump(mode="json")
    else:
        blocks = get_language_blocks(language)
        data_dict = blocks.model_dump(mode="json")

    json_str = json.dumps(data_dict, indent=2)

    if output:
        Path(output).write_text(json_str)
        click.echo(f"Block data written to: {output}")
    else:
        click.echo(json_str)


@cli.command("list")
@click.option(
    "-l", "--language",
    type=click.Choice(["python", "c", "octave", "r", "julia", "fortran", "document"], case_sensitive=False),
    help="Show blocks for specific language only"
)
def list_blocks(language):
    """List available test types and qualifications.

    Examples:

        blocks list              # List all languages
        blocks list -l python    # List Python blocks
    """
    if language:
        languages = [get_language_blocks(language)]
    else:
        registry = get_all_blocks()
        languages = registry.languages

    for lang in languages:
        click.echo(f"\n{click.style(lang.name, fg='cyan', bold=True)}")
        click.echo(f"  Extensions: {', '.join(lang.file_extensions)}")

        click.echo(f"\n  {click.style('Test Types:', fg='yellow')}")
        for tt in lang.test_types:
            click.echo(f"    - {tt.id}: {tt.description}")
            if tt.qualifications:
                quals = ", ".join(tt.qualifications)
                click.echo(f"      Qualifications: {quals}")

        click.echo(f"\n  {click.style('Qualifications:', fg='yellow')}")
        for qual in lang.qualifications:
            click.echo(f"    - {qual.id}: {qual.description}")


@cli.command()
@click.argument("output_dir", type=click.Path())
@click.option(
    "--prefix",
    default="blocks",
    help="Prefix for output files (default: blocks)"
)
def export(output_dir, prefix):
    """Export all formats to a directory.

    Exports:
      - {prefix}.schema.json   (JSON Schema)
      - {prefix}.types.ts      (TypeScript interfaces)
      - {prefix}.data.json     (Raw block data)

    Examples:

        blocks export ./generated
        blocks export ./src/types --prefix itp
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Export all formats
    schema_file = output_path / f"{prefix}.schema.json"
    export_json_schema(str(schema_file))
    click.echo(f"Wrote: {schema_file}")

    ts_file = output_path / f"{prefix}.types.ts"
    export_typescript(str(ts_file))
    click.echo(f"Wrote: {ts_file}")

    data_file = output_path / f"{prefix}.data.json"
    registry = get_all_blocks()
    data_file.write_text(json.dumps(registry.model_dump(mode="json"), indent=2))
    click.echo(f"Wrote: {data_file}")

    click.echo(click.style("\nAll files exported successfully!", fg="green"))


@cli.command("test-yaml-schema")
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output file path (prints to stdout if not specified)"
)
def test_yaml_schema(output):
    """Export JSON Schema for test.yaml files.

    This schema can be used by VSCode (via YAML extension) to provide
    validation and autocomplete for test.yaml files.

    Examples:

        blocks test-yaml-schema
        blocks test-yaml-schema -o test-yaml.schema.json
    """
    json_str = export_test_yaml_schema()

    if output:
        Path(output).write_text(json_str)
        click.echo(f"test.yaml JSON Schema written to: {output}")
    else:
        click.echo(json_str)


@cli.command("visibility")
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output file path (prints to stdout if not specified)"
)
def visibility(output):
    """Export field visibility map as JSON.

    Shows which fields are relevant for each (language, test_type, qualification)
    combination. Used by VSCode extension for dynamic form rendering.

    Examples:

        blocks visibility
        blocks visibility -o visibility.json
    """
    json_str = export_field_visibility()

    if output:
        Path(output).write_text(json_str)
        click.echo(f"Field visibility map written to: {output}")
    else:
        click.echo(json_str)


# =============================================================================
# Template Commands
# =============================================================================

@cli.group()
def templates():
    """Manage test.yaml templates.

    Templates are pre-built YAML snippets for common test scenarios.
    """
    pass


@templates.command("list")
@click.option(
    "-l", "--language",
    type=click.Choice(["python", "c", "octave", "r", "julia", "fortran", "document"], case_sensitive=False),
    help="Filter by language"
)
@click.option(
    "-t", "--test-type",
    help="Filter by test type (e.g., variable, stdout)"
)
def list_templates(language, test_type):
    """List available templates.

    Examples:

        blocks templates list
        blocks templates list -l python
        blocks templates list -l c -t stdout
    """
    if test_type and language:
        templates_list = get_templates_by_test_type(language, test_type)
    elif language:
        templates_list = get_templates(language)
    else:
        templates_list = get_templates()

    if not templates_list:
        click.echo("No templates found.")
        return

    # Group by language
    by_lang = {}
    for t in templates_list:
        by_lang.setdefault(t.language, []).append(t)

    for lang, tpls in by_lang.items():
        lang_name = {"python": "Python", "c": "C/C++", "octave": "Octave/MATLAB", "r": "R", "julia": "Julia", "fortran": "Fortran", "document": "Document"}.get(lang, lang)
        click.echo(f"\n{click.style(lang_name, fg='cyan', bold=True)}")

        for t in tpls:
            click.echo(f"  {click.style(t.name, fg='yellow')} ({t.test_type})")
            click.echo(f"    {t.description}")


@templates.command("show")
@click.argument("template_name")
@click.option(
    "-l", "--language",
    type=click.Choice(["python", "c", "octave", "r", "julia", "fortran", "document"], case_sensitive=False),
    help="Language (required if template name is ambiguous)"
)
def show_template(template_name, language):
    """Show a specific template's YAML snippet.

    Examples:

        blocks templates show "Variable Check" -l python
        blocks templates show "Exit Code" -l c
    """
    templates_list = get_templates(language) if language else get_templates()

    # Find matching template
    matches = [t for t in templates_list if t.name.lower() == template_name.lower()]

    if not matches:
        # Try partial match
        matches = [t for t in templates_list if template_name.lower() in t.name.lower()]

    if not matches:
        click.echo(f"No template found matching '{template_name}'")
        return

    if len(matches) > 1 and not language:
        click.echo(f"Multiple templates found. Please specify language with -l:")
        for t in matches:
            click.echo(f"  - {t.name} ({t.language})")
        return

    template = matches[0]
    click.echo(f"\n{click.style(template.name, fg='cyan', bold=True)} ({template.language})")
    click.echo(f"{template.description}\n")
    click.echo(click.style("YAML Snippet:", fg='yellow'))
    click.echo(template.yaml_snippet)

    if template.placeholders:
        click.echo(click.style("\nPlaceholders:", fg='yellow'))
        for key, desc in template.placeholders.items():
            click.echo(f"  {key}: {desc}")


@templates.command("export")
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output file path"
)
@click.option(
    "-l", "--language",
    type=click.Choice(["python", "c", "octave", "r", "julia", "fortran", "document"], case_sensitive=False),
    help="Filter by language"
)
def export_templates(output, language):
    """Export templates as JSON.

    Examples:

        blocks templates export -o templates.json
        blocks templates export -l python -o python-templates.json
    """
    if language:
        templates_list = get_templates(language)
        data = {
            "version": "1.0",
            "language": language,
            "templates": [t.model_dump(mode="json") for t in templates_list]
        }
    else:
        data = json.loads(export_templates_json())

    json_str = json.dumps(data, indent=2)

    if output:
        Path(output).write_text(json_str)
        click.echo(f"Templates written to: {output}")
    else:
        click.echo(json_str)


@cli.command("generate")
@click.option(
    "-l", "--language",
    type=click.Choice(["python", "c", "octave", "r", "julia", "fortran", "document"], case_sensitive=False),
    required=True,
    help="Target language"
)
@click.option(
    "-t", "--test-type",
    required=True,
    help="Test type (e.g., variable, stdout, exitcode)"
)
@click.option(
    "-n", "--name",
    default="test",
    help="Test name"
)
@click.option(
    "-c", "--collection-name",
    default="Test Collection",
    help="Collection name"
)
@click.option(
    "-e", "--entry-point",
    help="Entry point file"
)
@click.option(
    "-q", "--qualification",
    help="Qualification type"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output file (appends if exists)"
)
def generate(language, test_type, name, collection_name, entry_point, qualification, output):
    """Generate a test.yaml snippet.

    Examples:

        blocks generate -l python -t variable -n result
        blocks generate -l c -t stdout -q contains -e main.c
        blocks generate -l octave -t variable -n x -o test.yaml
    """
    try:
        yaml_str = generate_test_yaml(
            language=language,
            test_type=test_type,
            test_name=name,
            collection_name=collection_name,
            entry_point=entry_point,
            qualification=qualification,
        )

        if output:
            output_path = Path(output)
            if output_path.exists():
                # Append to existing file
                existing = output_path.read_text()
                if existing.strip():
                    # Add to properties.tests array
                    yaml_str = "\n" + yaml_str
                output_path.write_text(existing + yaml_str)
                click.echo(f"Appended to: {output}")
            else:
                output_path.write_text(yaml_str)
                click.echo(f"Written to: {output}")
        else:
            click.echo(yaml_str)

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command("init")
@click.option(
    "-l", "--language",
    type=click.Choice(["python", "c", "octave", "r", "julia", "fortran", "document"], case_sensitive=False),
    required=True,
    help="Target language"
)
@click.option(
    "-n", "--name",
    default="Tests",
    help="Test suite name"
)
@click.option(
    "-d", "--description",
    help="Test suite description"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    default="test.yaml",
    help="Output file (default: test.yaml)"
)
def init_test_yaml(language, name, description, output):
    """Initialize a new test.yaml file.

    Creates a complete test.yaml structure with language-appropriate defaults.

    Examples:

        blocks init -l python
        blocks init -l c -n "Calculator Tests" -o tests/test.yaml
    """
    yaml_str = generate_full_test_yaml(
        language=language,
        name=name,
        description=description,
    )

    output_path = Path(output)
    if output_path.exists():
        click.confirm(f"{output} already exists. Overwrite?", abort=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml_str)
    click.echo(f"Created: {output}")
    click.echo(f"\nUse 'blocks generate' or 'blocks templates' to add tests.")


if __name__ == "__main__":
    cli()
