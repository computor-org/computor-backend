#!/usr/bin/env python3
"""
Script to update all imports from old models.py to new sqlalchemy_models structure.
"""

import os
import re
import sys
from pathlib import Path

# Mapping of old model imports to new structure
MODEL_MAPPINGS = {
    # Auth models
    'User': 'sqlalchemy_models.auth',
    'Account': 'sqlalchemy_models.auth', 
    'Profile': 'sqlalchemy_models.auth',
    'StudentProfile': 'sqlalchemy_models.auth',
    'Session': 'sqlalchemy_models.auth',
    
    # Organization
    'Organization': 'sqlalchemy_models.organization',
    
    # Course models  
    'CourseContentKind': 'sqlalchemy_models.course',
    'CourseRole': 'sqlalchemy_models.course',
    'CourseFamily': 'sqlalchemy_models.course',
    'Course': 'sqlalchemy_models.course',
    'CourseContentType': 'sqlalchemy_models.course',
    'CourseExecutionBackend': 'sqlalchemy_models.course',
    'CourseGroup': 'sqlalchemy_models.course',
    'CourseContent': 'sqlalchemy_models.course',
    'CourseMember': 'sqlalchemy_models.course',
    'SubmissionGroup': 'sqlalchemy_models.course',
    'SubmissionGroupMember': 'sqlalchemy_models.course',
    'CourseMemberComment': 'sqlalchemy_models.course',
    
    # Execution
    'ExecutionBackend': 'sqlalchemy_models.execution',
    
    # Result
    'Result': 'sqlalchemy_models.result',
    
    # Role/Permission models
    'Role': 'sqlalchemy_models.role',
    'RoleClaim': 'sqlalchemy_models.role',
    'UserRole': 'sqlalchemy_models.role',
    
    # Group models
    'Group': 'sqlalchemy_models.group',
    'GroupClaim': 'sqlalchemy_models.group',
    'UserGroup': 'sqlalchemy_models.group',
    
    # Message models
    'Message': 'sqlalchemy_models.message',
    'MessageRead': 'sqlalchemy_models.message'
}

def update_file_imports(file_path):
    """Update imports in a single file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern for imports from models
        old_import_pattern = r'from\s+computor_backend\.model\.models\s+import\s+([^;\n]+)'
        
        def replace_import(match):
            imports_str = match.group(1)
            # Split by commas and clean up
            imports = [imp.strip() for imp in imports_str.split(',')]
            
            # Group imports by their new modules
            import_groups = {}
            for imp in imports:
                if imp in MODEL_MAPPINGS:
                    module = MODEL_MAPPINGS[imp]
                    if module not in import_groups:
                        import_groups[module] = []
                    import_groups[module].append(imp)
                else:
                    print(f"⚠️  Unknown model '{imp}' in {file_path}")
            
            # Generate new import statements
            new_imports = []
            for module, models in import_groups.items():
                new_imports.append(f"from computor_backend.model.{module} import {', '.join(models)}")
            
            return '\n'.join(new_imports)
        
        # Replace the imports
        content = re.sub(old_import_pattern, replace_import, content, flags=re.MULTILINE)
        
        # Also handle model.__init__ imports
        content = re.sub(
            r'from\s+computor_backend\.model\s+import\s+\*',
            'from computor_backend.model import *',
            content
        )
        
        # Handle specific model imports like "ngle_import_pattern = r'from\s+computor_backend\.model\s+import\s+([^;\\n]+)'
        
        def replace_single_import(match):
            imports_str = match.group(1)
            imports = [imp.strip() for imp in imports_str.split(',')]
            
            # Group imports by their new modules
            import_groups = {}
            for imp in imports:
                if imp in MODEL_MAPPINGS:
                    module = MODEL_MAPPINGS[imp]
                    if module not in import_groups:
                        import_groups[module] = []
                    import_groups[module].append(imp)
                else:
                    print(f"⚠️  Unknown model '{imp}' in {file_path}")
            
            # Generate new import statements
            new_imports = []
            for module, models in import_groups.items():
                new_imports.append(f"from computor_backend.model.{module} import {', '.join(models)}")
            
            return '\\n'.join(new_imports)
        
        content = re.sub(old_single_import_pattern, replace_single_import, content, flags=re.MULTILINE)
        
        # Handle relative imports in model directory
        if 'model/' in str(file_path):
            content = re.sub(
                r'from\s+\.models\s+import\s+([^;\n]+)',
                lambda m: replace_import(m).replace('computor_backend.model.', '.'),
                content
            )
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Updated {file_path}")
            return True
        else:
            print(f"⏭️  No changes needed in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False

def find_python_files():
    """Find all Python files that might need updating."""
    python_files = []
    
    # Search in specific directories
    search_dirs = ['api', 'interface', 'model', '.']
    
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for root, dirs, files in os.walk(search_dir):
                # Skip __pycache__ and .git directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
    
    return python_files

def main():
    """Main function to update all imports."""
    print("🔄 Updating imports from old models.py to new sqlalchemy_models structure")
    print("=" * 80)
    
    # Find all Python files
    python_files = find_python_files()
    print(f"Found {len(python_files)} Python files to check")
    
    updated_count = 0
    for file_path in python_files:
        if update_file_imports(file_path):
            updated_count += 1
    
    print("=" * 80)
    print(f"✅ Updated {updated_count} files")
    
    # Also need to update the model/__init__.py
    print("\n🔄 Updating model/__init__.py")
    init_file = "model/__init__.py"
    if os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write("from .sqlalchemy_models import *\n")
        print(f"✅ Updated {init_file}")
    
    print("\n🎉 Import updates completed!")

if __name__ == '__main__':
    main()