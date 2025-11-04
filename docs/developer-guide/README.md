# Developer Guide Index

This directory contains detailed developer guides for the Computor platform.

## Available Guides

### Getting Started

1. **[Getting Started](01-getting-started.md)**
   - Prerequisites and required software
   - Initial setup and installation
   - Environment configuration
   - Verification steps
   - Common setup issues

2. **[Code Organization](02-code-organization.md)**
   - Monorepo structure (4 packages)
   - Directory layout for each package
   - File naming conventions
   - Import patterns
   - Configuration files

3. **[Development Workflow](03-development-workflow.md)**
   - Daily development cycle
   - Creating feature branches
   - Making changes (adding entities, modifying endpoints)
   - Testing workflow
   - Git commit conventions
   - Creating pull requests

### Core Architecture

4. **[Backend Architecture](04-backend-architecture.md)**
   - Layered architecture overview
   - API Layer (thin endpoints)
   - Permission Layer (RBAC)
   - Business Logic Layer (fat logic)
   - Repository Layer (data access)
   - Model Layer (SQLAlchemy ORM)
   - Task Layer (Temporal workflows)
   - Service Layer (infrastructure)
   - Design patterns and best practices

5. **[EntityInterface Pattern](05-entityinterface-pattern.md)**
   - What is EntityInterface
   - DTO types (Create, Get, List, Update, Query)
   - Base classes
   - Code generation (Python client, TypeScript)
   - Backend integration
   - Advanced patterns
   - Best practices

6. **[Permission System](06-permission-system.md)**
   - RBAC overview
   - Principal and Claims
   - Role hierarchy
   - Permission checking patterns
   - Permission handlers
   - Common scenarios
   - Testing permissions
   - Best practices

### Database & Async Operations

7. **[Database & Migrations](07-database-migrations.md)**
   - Database architecture
   - SQLAlchemy models
   - Alembic migrations
   - Creating and applying migrations
   - Session management
   - Querying patterns
   - Database utilities
   - Testing with database
   - Troubleshooting

8. **[Temporal Workflows](08-temporal-workflows.md)**
   - What is Temporal
   - Architecture components
   - Workflows and activities
   - Common patterns
   - Starting workflows from API
   - Checking workflow status
   - Real workflow examples
   - Running workers
   - Monitoring and best practices

## Guides In Progress

The following guides are referenced but not yet written:

9. **Repository Pattern** - Data access layer, complex queries
10. **API Development** - Creating and extending REST endpoints
11. **Testing Guide** - Unit tests, integration tests, test patterns
13. **Type Generation** - TypeScript interface and client generation
14. **CLI Usage** - Command-line tools and utilities
15. **Configuration Management** - Environment variables and settings
16. **Docker & Services** - Docker Compose, service management
17. **Troubleshooting** - Common issues and solutions

## How to Use These Guides

### For New Developers

Start here:
1. [Getting Started](01-getting-started.md) - Set up your environment
2. [Code Organization](02-code-organization.md) - Understand the codebase
3. [Development Workflow](03-development-workflow.md) - Learn daily practices
4. [Backend Architecture](04-backend-architecture.md) - Understand system design

### For Specific Tasks

- **Adding new entity**: See [Development Workflow](03-development-workflow.md#adding-new-entities)
- **Implementing permissions**: See [Permission System](06-permission-system.md)
- **Creating database migration**: See [Database & Migrations](07-database-migrations.md)
- **Creating async workflow**: See [Temporal Workflows](08-temporal-workflows.md)

### For Reference

- **DTO patterns**: [EntityInterface Pattern](05-entityinterface-pattern.md)
- **Database queries**: [Database & Migrations](07-database-migrations.md#querying)
- **Permission patterns**: [Permission System](06-permission-system.md#permission-checking-patterns)
- **Architecture layers**: [Backend Architecture](04-backend-architecture.md#layer-details)

## Contributing to Documentation

When adding or updating guides:

1. **Follow the existing format**:
   - Start with overview/introduction
   - Provide code examples
   - Include best practices section
   - End with "Next Steps" linking to related guides

2. **Use consistent formatting**:
   - Code blocks with language specified
   - Clear section headings
   - ✅ Good / ❌ Bad examples
   - Links to related content

3. **Keep examples practical**:
   - Use actual code patterns from the codebase
   - Show complete, runnable examples
   - Explain why, not just what

4. **Update cross-references**:
   - Add links to/from related guides
   - Update main [guideline.md](../guideline.md)
   - Update this README

## Quick Reference Links

- **Main Guideline**: [guideline.md](../guideline.md)
- **Architecture Overview**: [architecture-overview.md](../architecture-overview.md)
- **CLAUDE.md**: [CLAUDE.md](../../CLAUDE.md)
- **API Documentation**: http://localhost:8000/docs (when server running)

---

**Last Updated**: 2025-10-23
