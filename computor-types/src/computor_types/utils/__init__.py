"""Pure helpers shared by the computor_types DTOs.

Must stay dependency-free (stdlib only): computor_types is imported by the
backend, the generated clients and the codegen, and may never import
computor_backend (see scripts/check_forbidden_imports.py).
"""
