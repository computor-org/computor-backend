#!/usr/bin/env python3
"""
Migration script to clean up computor-types package.
Removes backend-specific imports (models, SQLAlchemy sessions).
"""

import re
from pathlib import Path

TYPES_DIR = Path(__file__).parent.parent / "computor-types" / "src" / "computor_types"

def remove_model_imports(file_path: Path):
    """Remove model imports and make them TYPE_CHECKING only."""
    content = file_path.read_text()

    # Remove direct model imports
    content = re.sub(
        r'^from ctutor_backend\.model\..*$',
        '',
        content,
        flags=re.MULTILINE
    )

    # Remove SQLAlchemy Session imports if they exist
    content = re.sub(
        r'^from sqlalchemy\.orm import Session.*$',
        '',
        content,
        flags=re.MULTILINE
    )

    # Fix relative imports for custom_types
    content = content.replace('from ..custom_types', 'from computor_types.custom_types')

    # Clean up multiple blank lines
    content = re.sub(r'\n\n\n+', '\n\n', content)

    file_path.write_text(content)
    print(f"✅ Cleaned {file_path.name}")

def update_entity_interface_base(base_file: Path):
    """Update base.py to make model optional."""
    content = base_file.read_text()

    # Model field should be Optional[Any] instead of Any
    if 'model: Any = None' not in content:
        content = content.replace('model: Any', 'model: Any = None  # Optional: Set by backend')

    base_file.write_text(content)
    print(f"✅ Updated {base_file.name} - made model optional")

def main():
    """Run migration."""
    print("🔄 Migrating computor-types package...")

    # Update base.py first
    base_file = TYPES_DIR / "base.py"
    if base_file.exists():
        update_entity_interface_base(base_file)

    # Process all Python files
    for py_file in TYPES_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        remove_model_imports(py_file)

    print("\n✅ Migration complete!")
    print("\nNote: Some interfaces reference models in search functions.")
    print("These will need to be set by the backend when using EntityInterface.")

if __name__ == "__main__":
    main()
