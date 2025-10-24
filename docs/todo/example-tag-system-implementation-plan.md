# Example Tag System Implementation Plan (Option B)

**Document Version:** 1.0
**Date:** 2025-10-24
**Status:** Planning

---

## 📋 Executive Summary

This document outlines the implementation plan for a **structured, namespaced tag taxonomy system** for the Computor example library. The system uses `category:value` format tags stored in dedicated database tables with proper metadata and relationships.

### Key Goals

- ✅ Enable multi-dimensional filtering of examples (subject, difficulty, tool, format, etc.)
- ✅ Support hierarchical tag relationships (e.g., `topic:linear-algebra` → `topic:matrices`)
- ✅ Provide tag metadata (titles, descriptions, colors, icons) for rich UI
- ✅ Maintain flexibility for adding new tag categories
- ✅ Support both Example and ExampleVersion level tagging
- ✅ Add public/private visibility control

---

## 🏗️ Architecture Overview

### Database Schema

```
┌─────────────────────┐         ┌──────────────────────┐
│   Example           │         │   ExampleTag         │
├─────────────────────┤         ├──────────────────────┤
│ id (UUID)           │         │ id (UUID)            │
│ title               │         │ tag (string)         │
│ subject             │◄────┐   │ category (string)    │
│ difficulty_level    │     │   │ value (string)       │
│ tags (ARRAY)        │     │   │ title                │
│ is_public (bool)    │     │   │ description          │
└─────────────────────┘     │   │ color                │
                            │   │ icon                 │
┌─────────────────────┐     │   │ parent_id (UUID)     │
│ ExampleVersion      │     │   └──────────────────────┘
├─────────────────────┤     │              │
│ id (UUID)           │     │              │ parent/children
│ example_id          │     │              │
│ meta_language       │     │              ▼
│ primary_tool        │     │   ┌──────────────────────┐
│ grading_method      │     │   │ ExampleTagAssignment │
│ duration_minutes    │     │   ├──────────────────────┤
│ meta_yaml           │     └───┤ example_id (FK)      │
└─────────────────────┘         │ tag_id (FK)          │
                                └──────────────────────┘
┌─────────────────────┐
│ ExampleRepository   │
├─────────────────────┤
│ id (UUID)           │
│ organization_id     │
│ is_public (bool)    │◄── NEW
└─────────────────────┘
```

### Tag Format Specification

**Format:** `category:value`

**Examples:**
- `domain:mathematics`
- `topic:linear-algebra`
- `difficulty:intermediate`
- `tool:python`
- `format:code`
- `grading:automated`

**Validation Rules:**
- Category: `[a-z0-9-]+` (lowercase alphanumeric + hyphens)
- Value: `[a-z0-9-]+` (lowercase alphanumeric + hyphens)
- Combined: Regex `^[a-z0-9-]+:[a-z0-9-]+$`

---

## 📊 Phase 1: Database Schema Changes

### 1.1 Create ExampleTag Table

**File:** `computor-backend/src/computor_backend/model/example.py`

```python
class ExampleTag(Base):
    """
    Tag definition with category and value.

    Tags follow the format "category:value" (e.g., "domain:mathematics").
    Provides metadata for UI display and supports hierarchical relationships.
    """

    __tablename__ = "example_tag"

    # Primary key
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))

    # Namespaced tag format
    tag = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Full tag in format 'category:value' (e.g., 'domain:mathematics')"
    )

    # Parsed components
    category = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Tag category (e.g., 'domain', 'topic', 'difficulty')"
    )
    value = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Tag value (e.g., 'mathematics', 'beginner')"
    )

    # Display metadata
    title = Column(String(255), comment="Human-readable title (e.g., 'Mathematics')")
    description = Column(Text, comment="Detailed description of what this tag represents")
    color = Column(String(20), comment="UI color in hex format (e.g., '#4CAF50')")
    icon = Column(String(50), comment="Icon identifier for UI (e.g., 'calculator', 'code')")

    # Hierarchical support
    parent_id = Column(
        UUID,
        ForeignKey("example_tag.id", ondelete="SET NULL"),
        comment="Parent tag for hierarchical relationships"
    )

    # Tracking
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID, ForeignKey("user.id", ondelete="SET NULL"))
    updated_by = Column(UUID, ForeignKey("user.id", ondelete="SET NULL"))

    # Relationships
    parent = relationship("ExampleTag", remote_side=[id], back_populates="children")
    children = relationship("ExampleTag", back_populates="parent")
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])
    example_assignments = relationship("ExampleTagAssignment", back_populates="tag", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("category", "value", name="unique_category_value"),
        Index("idx_tag_category", "category"),
        Index("idx_tag_value", "value"),
        Index("idx_tag_full", "tag"),
        CheckConstraint(
            "tag ~ '^[a-z0-9-]+:[a-z0-9-]+$'",
            name="check_tag_format"
        ),
        CheckConstraint(
            "category IN ("
            "'domain', 'topic', 'difficulty', 'language', 'tool', "
            "'format', 'grading', 'duration', 'cognitive', 'strategy', "
            "'skill', 'accessibility', 'custom'"
            ")",
            name="check_tag_category"
        ),
    )

    def __repr__(self):
        return f"<ExampleTag(tag='{self.tag}', title='{self.title}')>"
```

### 1.2 Create ExampleTagAssignment Table

```python
class ExampleTagAssignment(Base):
    """
    Many-to-many relationship between Examples and Tags.

    Links examples to their associated tags for filtering and categorization.
    """

    __tablename__ = "example_tag_assignment"

    # Primary key
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))

    # Foreign keys
    example_id = Column(
        UUID,
        ForeignKey("example.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the example"
    )
    tag_id = Column(
        UUID,
        ForeignKey("example_tag.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the tag"
    )

    # Tracking
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(UUID, ForeignKey("user.id", ondelete="SET NULL"))

    # Relationships
    example = relationship("Example", back_populates="tag_assignments")
    tag = relationship("ExampleTag", back_populates="example_assignments")
    created_by_user = relationship("User", foreign_keys=[created_by])

    # Constraints
    __table_args__ = (
        UniqueConstraint("example_id", "tag_id", name="unique_example_tag"),
        Index("idx_example_tag_assignment_example", "example_id"),
        Index("idx_example_tag_assignment_tag", "tag_id"),
    )

    def __repr__(self):
        return f"<ExampleTagAssignment(example_id={self.example_id}, tag_id={self.tag_id})>"
```

### 1.3 Update Example Table

**Add to existing `Example` model:**

```python
class Example(Base):
    # ... existing fields ...

    # ADD NEW FIELDS:
    subject = Column(
        String(100),
        index=True,
        comment="Subject area (e.g., 'Linear Algebra', 'Data Structures')"
    )
    difficulty_level = Column(
        String(20),
        index=True,
        comment="Difficulty: beginner, elementary, intermediate, advanced, expert"
    )
    is_public = Column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="If true, visible to all organizations"
    )

    # KEEP EXISTING:
    category = Column(String(100), comment="Category for grouping examples")
    tags = Column(ARRAY(String), nullable=False, default=[], comment="Legacy tags array")

    # ADD NEW RELATIONSHIP:
    tag_assignments = relationship("ExampleTagAssignment", back_populates="example", cascade="all, delete-orphan")
```

### 1.4 Update ExampleVersion Table

**Add to existing `ExampleVersion` model:**

```python
class ExampleVersion(Base):
    # ... existing fields ...

    # ADD NEW FIELDS (extracted from meta.yaml for queryability):

    # Meta information
    meta_version = Column(String(20), comment="Meta format version (e.g., '1.0')")
    meta_language = Column(
        String(10),
        index=True,
        comment="Content language code (e.g., 'en', 'de', 'fr')"
    )
    meta_license = Column(String(255), comment="License information")
    meta_keywords = Column(
        ARRAY(String),
        index=True,
        comment="Keywords from meta.yaml for search"
    )

    # Tool/Technology
    primary_tool = Column(
        String(50),
        index=True,
        comment="Primary tool/language (e.g., 'python', 'matlab', 'java')"
    )

    # Execution/Grading
    execution_backend_slug = Column(
        String(255),
        index=True,
        comment="Execution backend identifier"
    )
    execution_backend_version = Column(
        String(100),
        comment="Execution backend version (e.g., 'r2024b', '3.11')"
    )
    grading_method = Column(
        String(50),
        index=True,
        comment="Grading method: automated, manual, peer-review, etc."
    )

    # Educational metadata
    difficulty_level = Column(
        String(20),
        index=True,
        comment="Can override example.difficulty_level"
    )
    cognitive_level = Column(
        String(20),
        comment="Bloom's taxonomy level: remember, understand, apply, analyze, evaluate, create"
    )
    estimated_duration_minutes = Column(
        Integer,
        comment="Estimated completion time in minutes"
    )

    # Assessment-specific (for quizzes/exams)
    question_count = Column(Integer, comment="Number of questions (for quizzes/exams)")
    passing_score = Column(Float, comment="Minimum percentage to pass")

    # KEEP EXISTING:
    meta_yaml = Column(Text, nullable=False, comment="Complete meta.yaml content")
    test_yaml = Column(Text, nullable=True, comment="Complete test.yaml content")
```

### 1.5 Update ExampleRepository Table

**Add to existing `ExampleRepository` model:**

```python
class ExampleRepository(Base):
    # ... existing fields ...

    # ADD NEW FIELD:
    is_public = Column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="If true, all examples in this repository are visible to all organizations"
    )
```

---

## 📝 Phase 2: Database Migration

### 2.1 Create Alembic Migration

**File:** `computor-backend/src/computor_backend/alembic/versions/XXXXX_add_example_tag_system.py`

**Command:**
```bash
cd computor-backend/src
alembic revision -m "add example tag system with structured taxonomy"
```

**Migration content:**

```python
"""add example tag system with structured taxonomy

Revision ID: XXXXX
Revises: YYYYY
Create Date: 2025-10-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'XXXXX'
down_revision = 'YYYYY'
branch_labels = None
depends_on = None

def upgrade():
    # Create example_tag table
    op.create_table(
        'example_tag',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tag', sa.String(length=100), nullable=False, comment="Full tag in format 'category:value'"),
        sa.Column('category', sa.String(length=50), nullable=False, comment='Tag category'),
        sa.Column('value', sa.String(length=50), nullable=False, comment='Tag value'),
        sa.Column('title', sa.String(length=255), comment='Human-readable title'),
        sa.Column('description', sa.Text(), comment='Detailed description'),
        sa.Column('color', sa.String(length=20), comment='UI color in hex format'),
        sa.Column('icon', sa.String(length=50), comment='Icon identifier'),
        sa.Column('parent_id', postgresql.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['example_tag.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tag', name='example_tag_tag_key'),
        sa.UniqueConstraint('category', 'value', name='unique_category_value'),
        sa.CheckConstraint("tag ~ '^[a-z0-9-]+:[a-z0-9-]+$'", name='check_tag_format'),
        sa.CheckConstraint(
            "category IN ('domain', 'topic', 'difficulty', 'language', 'tool', "
            "'format', 'grading', 'duration', 'cognitive', 'strategy', "
            "'skill', 'accessibility', 'custom')",
            name='check_tag_category'
        )
    )
    op.create_index('idx_tag_category', 'example_tag', ['category'])
    op.create_index('idx_tag_value', 'example_tag', ['value'])
    op.create_index('idx_tag_full', 'example_tag', ['tag'])

    # Create example_tag_assignment table
    op.create_table(
        'example_tag_assignment',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('example_id', postgresql.UUID(), nullable=False),
        sa.Column('tag_id', postgresql.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['example_id'], ['example.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['example_tag.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('example_id', 'tag_id', name='unique_example_tag')
    )
    op.create_index('idx_example_tag_assignment_example', 'example_tag_assignment', ['example_id'])
    op.create_index('idx_example_tag_assignment_tag', 'example_tag_assignment', ['tag_id'])

    # Add new columns to example table
    op.add_column('example', sa.Column('subject', sa.String(length=100), comment='Subject area'))
    op.add_column('example', sa.Column('difficulty_level', sa.String(length=20), comment='Difficulty level'))
    op.add_column('example', sa.Column('is_public', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_index('idx_example_subject', 'example', ['subject'])
    op.create_index('idx_example_difficulty', 'example', ['difficulty_level'])

    # Add new columns to example_version table
    op.add_column('example_version', sa.Column('meta_version', sa.String(length=20)))
    op.add_column('example_version', sa.Column('meta_language', sa.String(length=10)))
    op.add_column('example_version', sa.Column('meta_license', sa.String(length=255)))
    op.add_column('example_version', sa.Column('meta_keywords', postgresql.ARRAY(sa.String())))
    op.add_column('example_version', sa.Column('primary_tool', sa.String(length=50)))
    op.add_column('example_version', sa.Column('execution_backend_slug', sa.String(length=255)))
    op.add_column('example_version', sa.Column('execution_backend_version', sa.String(length=100)))
    op.add_column('example_version', sa.Column('grading_method', sa.String(length=50)))
    op.add_column('example_version', sa.Column('difficulty_level', sa.String(length=20)))
    op.add_column('example_version', sa.Column('cognitive_level', sa.String(length=20)))
    op.add_column('example_version', sa.Column('estimated_duration_minutes', sa.Integer()))
    op.add_column('example_version', sa.Column('question_count', sa.Integer()))
    op.add_column('example_version', sa.Column('passing_score', sa.Float()))
    op.create_index('idx_example_version_language', 'example_version', ['meta_language'])
    op.create_index('idx_example_version_tool', 'example_version', ['primary_tool'])
    op.create_index('idx_example_version_backend', 'example_version', ['execution_backend_slug'])
    op.create_index('idx_example_version_grading', 'example_version', ['grading_method'])

    # Add new column to example_repository table
    op.add_column('example_repository', sa.Column('is_public', sa.Boolean(), server_default=sa.text('false'), nullable=False))

def downgrade():
    # Remove columns from example_repository
    op.drop_column('example_repository', 'is_public')

    # Remove columns from example_version
    op.drop_index('idx_example_version_grading', 'example_version')
    op.drop_index('idx_example_version_backend', 'example_version')
    op.drop_index('idx_example_version_tool', 'example_version')
    op.drop_index('idx_example_version_language', 'example_version')
    op.drop_column('example_version', 'passing_score')
    op.drop_column('example_version', 'question_count')
    op.drop_column('example_version', 'estimated_duration_minutes')
    op.drop_column('example_version', 'cognitive_level')
    op.drop_column('example_version', 'difficulty_level')
    op.drop_column('example_version', 'grading_method')
    op.drop_column('example_version', 'execution_backend_version')
    op.drop_column('example_version', 'execution_backend_slug')
    op.drop_column('example_version', 'primary_tool')
    op.drop_column('example_version', 'meta_keywords')
    op.drop_column('example_version', 'meta_license')
    op.drop_column('example_version', 'meta_language')
    op.drop_column('example_version', 'meta_version')

    # Remove columns from example
    op.drop_index('idx_example_difficulty', 'example')
    op.drop_index('idx_example_subject', 'example')
    op.drop_column('example', 'is_public')
    op.drop_column('example', 'difficulty_level')
    op.drop_column('example', 'subject')

    # Drop example_tag_assignment table
    op.drop_index('idx_example_tag_assignment_tag', 'example_tag_assignment')
    op.drop_index('idx_example_tag_assignment_example', 'example_tag_assignment')
    op.drop_table('example_tag_assignment')

    # Drop example_tag table
    op.drop_index('idx_tag_full', 'example_tag')
    op.drop_index('idx_tag_value', 'example_tag')
    op.drop_index('idx_tag_category', 'example_tag')
    op.drop_table('example_tag')
```

### 2.2 Run Migration

```bash
cd computor-backend/src
alembic upgrade head
```

---

## 🌱 Phase 3: Seed Default Tags

### 3.1 Create Tag Seeder Script

**File:** `computor-backend/src/computor_backend/scripts/seed_example_tags.py`

```python
#!/usr/bin/env python3
"""
Seed default example tags into the database.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

from computor_backend.database import get_db
from computor_backend.model.example import ExampleTag

# Tag definitions with metadata
TAG_DEFINITIONS = [
    # Domain tags
    {
        "tag": "domain:computer-science",
        "category": "domain",
        "value": "computer-science",
        "title": "Computer Science",
        "description": "Topics related to computer science and programming",
        "color": "#2196F3",
        "icon": "code"
    },
    {
        "tag": "domain:mathematics",
        "category": "domain",
        "value": "mathematics",
        "title": "Mathematics",
        "description": "Mathematical concepts and problem-solving",
        "color": "#9C27B0",
        "icon": "calculator"
    },
    {
        "tag": "domain:physics",
        "category": "domain",
        "value": "physics",
        "title": "Physics",
        "description": "Physical sciences and phenomena",
        "color": "#FF9800",
        "icon": "atom"
    },
    {
        "tag": "domain:engineering",
        "category": "domain",
        "value": "engineering",
        "title": "Engineering",
        "description": "Engineering disciplines and applications",
        "color": "#607D8B",
        "icon": "cog"
    },
    {
        "tag": "domain:humanities",
        "category": "domain",
        "value": "humanities",
        "title": "Humanities",
        "description": "Literature, history, philosophy, and arts",
        "color": "#E91E63",
        "icon": "book"
    },
    {
        "tag": "domain:languages",
        "category": "domain",
        "value": "languages",
        "title": "Languages",
        "description": "Language learning and linguistics",
        "color": "#00BCD4",
        "icon": "language"
    },

    # Difficulty tags
    {
        "tag": "difficulty:beginner",
        "category": "difficulty",
        "value": "beginner",
        "title": "Beginner",
        "description": "Suitable for beginners with no prior knowledge",
        "color": "#4CAF50",
        "icon": "star-outline"
    },
    {
        "tag": "difficulty:intermediate",
        "category": "difficulty",
        "value": "intermediate",
        "title": "Intermediate",
        "description": "Requires some foundational knowledge",
        "color": "#FF9800",
        "icon": "star-half"
    },
    {
        "tag": "difficulty:advanced",
        "category": "difficulty",
        "value": "advanced",
        "title": "Advanced",
        "description": "Challenging content for experienced learners",
        "color": "#F44336",
        "icon": "star"
    },

    # Language tags
    {
        "tag": "language:en",
        "category": "language",
        "value": "en",
        "title": "English",
        "description": "Content in English",
        "color": "#2196F3",
        "icon": "flag-gb"
    },
    {
        "tag": "language:de",
        "category": "language",
        "value": "de",
        "title": "German / Deutsch",
        "description": "Content in German",
        "color": "#000000",
        "icon": "flag-de"
    },

    # Tool tags - Programming Languages
    {
        "tag": "tool:python",
        "category": "tool",
        "value": "python",
        "title": "Python",
        "description": "Python programming language",
        "color": "#3776AB",
        "icon": "language-python"
    },
    {
        "tag": "tool:java",
        "category": "tool",
        "value": "java",
        "title": "Java",
        "description": "Java programming language",
        "color": "#007396",
        "icon": "language-java"
    },
    {
        "tag": "tool:matlab",
        "category": "tool",
        "value": "matlab",
        "title": "MATLAB",
        "description": "MATLAB numerical computing environment",
        "color": "#E16737",
        "icon": "chart-line"
    },

    # Format tags
    {
        "tag": "format:code",
        "category": "format",
        "value": "code",
        "title": "Code Submission",
        "description": "Programming code submission",
        "color": "#2196F3",
        "icon": "file-code"
    },
    {
        "tag": "format:essay",
        "category": "format",
        "value": "essay",
        "title": "Written Essay",
        "description": "Written essay or report",
        "color": "#795548",
        "icon": "file-document"
    },
    {
        "tag": "format:quiz",
        "category": "format",
        "value": "quiz",
        "title": "Quiz",
        "description": "Interactive quiz or test",
        "color": "#9C27B0",
        "icon": "help-circle"
    },

    # Grading tags
    {
        "tag": "grading:automated",
        "category": "grading",
        "value": "automated",
        "title": "Automated Grading",
        "description": "Automatically graded by system",
        "color": "#4CAF50",
        "icon": "robot"
    },
    {
        "tag": "grading:manual",
        "category": "grading",
        "value": "manual",
        "title": "Manual Grading",
        "description": "Graded by instructor",
        "color": "#FF9800",
        "icon": "account"
    },

    # Duration tags
    {
        "tag": "duration:short",
        "category": "duration",
        "value": "short",
        "title": "Short (<30 min)",
        "description": "Less than 30 minutes to complete",
        "color": "#4CAF50",
        "icon": "timer"
    },
    {
        "tag": "duration:medium",
        "category": "duration",
        "value": "medium",
        "title": "Medium (30-60 min)",
        "description": "30 to 60 minutes to complete",
        "color": "#FF9800",
        "icon": "timer"
    },
    {
        "tag": "duration:long",
        "category": "duration",
        "value": "long",
        "title": "Long (1-3 hours)",
        "description": "1 to 3 hours to complete",
        "color": "#F44336",
        "icon": "timer"
    },

    # Cognitive level tags (Bloom's Taxonomy)
    {
        "tag": "cognitive:remember",
        "category": "cognitive",
        "value": "remember",
        "title": "Remember",
        "description": "Recall facts and basic concepts",
        "color": "#E3F2FD",
        "icon": "brain"
    },
    {
        "tag": "cognitive:understand",
        "category": "cognitive",
        "value": "understand",
        "title": "Understand",
        "description": "Explain ideas or concepts",
        "color": "#BBDEFB",
        "icon": "brain"
    },
    {
        "tag": "cognitive:apply",
        "category": "cognitive",
        "value": "apply",
        "title": "Apply",
        "description": "Use information in new situations",
        "color": "#90CAF9",
        "icon": "brain"
    },
    {
        "tag": "cognitive:analyze",
        "category": "cognitive",
        "value": "analyze",
        "title": "Analyze",
        "description": "Draw connections and examine structure",
        "color": "#64B5F6",
        "icon": "brain"
    },
    {
        "tag": "cognitive:evaluate",
        "category": "cognitive",
        "value": "evaluate",
        "title": "Evaluate",
        "description": "Justify decisions and make judgments",
        "color": "#42A5F5",
        "icon": "brain"
    },
    {
        "tag": "cognitive:create",
        "category": "cognitive",
        "value": "create",
        "title": "Create",
        "description": "Produce new or original work",
        "color": "#2196F3",
        "icon": "brain"
    },
]

def seed_tags(db):
    """Seed example tags into the database."""
    print("🏷️  Seeding example tags...")

    created_count = 0
    updated_count = 0

    for tag_def in TAG_DEFINITIONS:
        existing_tag = db.query(ExampleTag).filter(ExampleTag.tag == tag_def["tag"]).first()

        if existing_tag:
            # Update existing tag
            existing_tag.title = tag_def.get("title")
            existing_tag.description = tag_def.get("description")
            existing_tag.color = tag_def.get("color")
            existing_tag.icon = tag_def.get("icon")
            updated_count += 1
            print(f"   ✏️  Updated: {tag_def['tag']}")
        else:
            # Create new tag
            new_tag = ExampleTag(**tag_def)
            db.add(new_tag)
            created_count += 1
            print(f"   ✅ Created: {tag_def['tag']}")

    db.commit()

    print(f"\n📊 Summary:")
    print(f"   Created: {created_count} tags")
    print(f"   Updated: {updated_count} tags")
    print(f"   Total: {len(TAG_DEFINITIONS)} tags")

if __name__ == "__main__":
    db = next(get_db())
    try:
        seed_tags(db)
        print("\n✅ Tag seeding completed successfully!")
    except Exception as e:
        print(f"\n❌ Error seeding tags: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()
```

### 3.2 Add to System Initialization

**Update:** `computor-backend/src/computor_backend/scripts/initialize_system_data.py`

Add call to seed tags:

```python
def main():
    # ... existing initialization ...

    # Seed example tags
    print("\n🏷️  Seeding example tags...")
    from computor_backend.scripts.seed_example_tags import seed_tags
    seed_tags(db)
```

---

## 🔧 Phase 4: Pydantic DTOs (computor-types)

### 4.1 Update Example DTOs

**File:** `computor-types/src/computor_types/example.py`

```python
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# ExampleTag DTOs
class ExampleTagCreate(BaseModel):
    """Create a new example tag."""
    tag: str = Field(..., pattern="^[a-z0-9-]+:[a-z0-9-]+$")
    category: str
    value: str
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[str] = None

class ExampleTagGet(BaseModel):
    """Get example tag details."""
    id: str
    tag: str
    category: str
    value: str
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Relationships
    parent: Optional['ExampleTagGet'] = None
    children: Optional[List['ExampleTagGet']] = None

    model_config = ConfigDict(from_attributes=True)

class ExampleTagList(BaseModel):
    """List view of tags."""
    id: str
    tag: str
    category: str
    value: str
    title: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ExampleTagUpdate(BaseModel):
    """Update example tag."""
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[str] = None

# Update ExampleCreate
class ExampleCreate(BaseModel):
    """Create a new example."""
    example_repository_id: str
    directory: str = Field(..., pattern="^[a-zA-Z0-9._-]+$")
    identifier: str
    title: str
    description: Optional[str] = None
    subject: Optional[str] = None  # NEW
    category: Optional[str] = None
    difficulty_level: Optional[str] = None  # NEW
    is_public: bool = False  # NEW
    tags: List[str] = Field(default_factory=list)  # Legacy array
    tag_ids: List[str] = Field(default_factory=list)  # NEW: References to ExampleTag IDs

# Update ExampleGet
class ExampleGet(BaseEntityGet, ExampleCreate):
    """Get example details."""
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    # Relationships
    repository: Optional[ExampleRepositoryGet] = None
    versions: Optional[List['ExampleVersionGet']] = None
    dependencies: Optional[List['ExampleDependencyGet']] = None
    assigned_tags: Optional[List[ExampleTagGet]] = None  # NEW

    model_config = ConfigDict(from_attributes=True)

# Update ExampleVersionCreate
class ExampleVersionCreate(BaseModel):
    """Create a new example version."""
    example_id: str
    version_tag: str
    version_number: int
    storage_path: str
    meta_yaml: str
    test_yaml: Optional[str] = None

    # NEW: Extracted meta fields
    meta_version: Optional[str] = None
    meta_language: Optional[str] = None
    meta_license: Optional[str] = None
    meta_keywords: Optional[List[str]] = None
    primary_tool: Optional[str] = None
    execution_backend_slug: Optional[str] = None
    execution_backend_version: Optional[str] = None
    grading_method: Optional[str] = None
    difficulty_level: Optional[str] = None
    cognitive_level: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    question_count: Optional[int] = None
    passing_score: Optional[float] = None

# Update ExampleQuery
class ExampleQuery(ListQuery):
    """Query parameters for listing examples."""
    id: Optional[str] = None
    repository_id: Optional[str] = None
    identifier: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None  # NEW
    category: Optional[str] = None
    difficulty_level: Optional[str] = None  # NEW
    is_public: Optional[bool] = None  # NEW
    tags: Optional[List[str]] = None
    tag_ids: Optional[List[str]] = None  # NEW: Filter by tag IDs
    tag_categories: Optional[List[str]] = None  # NEW: Filter by tag categories (e.g., "domain", "tool")
    search: Optional[str] = None
```

### 4.2 Update ExampleRepository DTOs

```python
class ExampleRepositoryCreate(BaseModel):
    """Create a new example repository."""
    name: str
    description: Optional[str] = None
    source_type: str = "git"
    source_url: str
    access_credentials: Optional[str] = None
    default_version: Optional[str] = None
    organization_id: Optional[str] = None
    is_public: bool = False  # NEW

class ExampleRepositoryGet(BaseEntityGet, ExampleRepositoryCreate):
    """Get example repository details."""
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
```

---

## 🚀 Phase 5: API Endpoints

### 5.1 Tag Management Endpoints

**File:** `computor-backend/src/computor_backend/api/example_tags.py`

```python
"""
API endpoints for Example Tag management.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.model.example import ExampleTag
from computor_types.example import ExampleTagCreate, ExampleTagGet, ExampleTagList, ExampleTagUpdate

router = APIRouter(prefix="/api/v1/example-tags", tags=["Example Tags"])

@router.get("", response_model=List[ExampleTagList])
async def list_tags(
    category: str = None,
    db: Session = Depends(get_db),
):
    """List all available example tags, optionally filtered by category."""
    query = db.query(ExampleTag)

    if category:
        query = query.filter(ExampleTag.category == category)

    tags = query.order_by(ExampleTag.category, ExampleTag.value).all()
    return tags

@router.get("/categories", response_model=List[str])
async def list_categories(db: Session = Depends(get_db)):
    """List all available tag categories."""
    categories = db.query(ExampleTag.category).distinct().all()
    return [cat[0] for cat in categories]

@router.get("/{tag_id}", response_model=ExampleTagGet)
async def get_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a specific tag by ID."""
    tag = db.query(ExampleTag).filter(ExampleTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag

@router.post("", response_model=ExampleTagGet)
async def create_tag(
    tag_data: ExampleTagCreate,
    db: Session = Depends(get_db),
    permissions = Depends(get_current_principal),
):
    """Create a new example tag (admin only)."""
    # Permission check: only admins can create tags
    if "_admin" not in permissions.global_roles:
        raise HTTPException(status_code=403, detail="Only admins can create tags")

    # Check if tag already exists
    existing = db.query(ExampleTag).filter(ExampleTag.tag == tag_data.tag).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tag already exists")

    tag = ExampleTag(**tag_data.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

@router.patch("/{tag_id}", response_model=ExampleTagGet)
async def update_tag(
    tag_id: UUID,
    tag_data: ExampleTagUpdate,
    db: Session = Depends(get_db),
    permissions = Depends(get_current_principal),
):
    """Update an example tag (admin only)."""
    if "_admin" not in permissions.global_roles:
        raise HTTPException(status_code=403, detail="Only admins can update tags")

    tag = db.query(ExampleTag).filter(ExampleTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    for field, value in tag_data.model_dump(exclude_unset=True).items():
        setattr(tag, field, value)

    db.commit()
    db.refresh(tag)
    return tag

@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    permissions = Depends(get_current_principal),
):
    """Delete an example tag (admin only)."""
    if "_admin" not in permissions.global_roles:
        raise HTTPException(status_code=403, detail="Only admins can delete tags")

    tag = db.query(ExampleTag).filter(ExampleTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    db.delete(tag)
    db.commit()
    return {"message": "Tag deleted successfully"}
```

### 5.2 Update Example Endpoints

**File:** `computor-backend/src/computor_backend/api/examples.py`

Add tag filtering logic:

```python
@router.get("", response_model=List[ExampleList])
async def list_examples(
    query: ExampleQuery = Depends(),
    db: Session = Depends(get_db),
):
    """List examples with filtering support."""
    q = db.query(Example)

    # ... existing filters ...

    # NEW: Filter by subject
    if query.subject:
        q = q.filter(Example.subject == query.subject)

    # NEW: Filter by difficulty
    if query.difficulty_level:
        q = q.filter(Example.difficulty_level == query.difficulty_level)

    # NEW: Filter by public status
    if query.is_public is not None:
        q = q.filter(Example.is_public == query.is_public)

    # NEW: Filter by tag IDs
    if query.tag_ids:
        q = q.join(ExampleTagAssignment).filter(
            ExampleTagAssignment.tag_id.in_(query.tag_ids)
        ).distinct()

    # NEW: Filter by tag categories
    if query.tag_categories:
        q = q.join(ExampleTagAssignment).join(ExampleTag).filter(
            ExampleTag.category.in_(query.tag_categories)
        ).distinct()

    return q.all()
```

### 5.3 Register Routers

**File:** `computor-backend/src/computor_backend/server.py`

```python
from computor_backend.api import example_tags

app.include_router(example_tags.router)
```

---

## 📚 Phase 6: Business Logic Layer

### 6.1 Tag Assignment Logic

**File:** `computor-backend/src/computor_backend/business_logic/examples.py`

```python
from typing import List
from sqlalchemy.orm import Session
from uuid import UUID

from computor_backend.model.example import Example, ExampleTag, ExampleTagAssignment

def assign_tags_to_example(
    example_id: UUID,
    tag_ids: List[UUID],
    db: Session,
    replace: bool = False
) -> Example:
    """
    Assign tags to an example.

    Args:
        example_id: Example to tag
        tag_ids: List of tag IDs to assign
        db: Database session
        replace: If True, replace all existing tags; if False, add to existing

    Returns:
        Updated Example instance
    """
    example = db.query(Example).filter(Example.id == example_id).first()
    if not example:
        raise ValueError(f"Example {example_id} not found")

    # Validate all tags exist
    tags = db.query(ExampleTag).filter(ExampleTag.id.in_(tag_ids)).all()
    if len(tags) != len(tag_ids):
        raise ValueError("One or more tag IDs are invalid")

    if replace:
        # Remove all existing tag assignments
        db.query(ExampleTagAssignment).filter(
            ExampleTagAssignment.example_id == example_id
        ).delete()

    # Add new tag assignments
    for tag_id in tag_ids:
        # Check if assignment already exists
        existing = db.query(ExampleTagAssignment).filter(
            ExampleTagAssignment.example_id == example_id,
            ExampleTagAssignment.tag_id == tag_id
        ).first()

        if not existing:
            assignment = ExampleTagAssignment(
                example_id=example_id,
                tag_id=tag_id
            )
            db.add(assignment)

    db.commit()
    db.refresh(example)
    return example

def remove_tags_from_example(
    example_id: UUID,
    tag_ids: List[UUID],
    db: Session
) -> Example:
    """Remove specific tags from an example."""
    db.query(ExampleTagAssignment).filter(
        ExampleTagAssignment.example_id == example_id,
        ExampleTagAssignment.tag_id.in_(tag_ids)
    ).delete()

    db.commit()

    example = db.query(Example).filter(Example.id == example_id).first()
    return example

def parse_meta_yaml_to_tags(meta_yaml_content: str, db: Session) -> List[UUID]:
    """
    Parse meta.yaml and extract/create appropriate tags.

    Returns list of tag IDs to assign to the example.
    """
    import yaml

    meta = yaml.safe_load(meta_yaml_content)
    tag_ids = []

    # Extract language
    if meta.get('language'):
        lang_tag = db.query(ExampleTag).filter(
            ExampleTag.tag == f"language:{meta['language']}"
        ).first()
        if lang_tag:
            tag_ids.append(lang_tag.id)

    # Extract keywords and map to tags
    keywords = meta.get('keywords', [])
    for keyword in keywords:
        # Try to find matching tag
        tag = db.query(ExampleTag).filter(
            ExampleTag.value == keyword.lower()
        ).first()
        if tag:
            tag_ids.append(tag.id)

    # Extract execution backend as tool tag
    if meta.get('properties', {}).get('executionBackend', {}).get('slug'):
        backend_slug = meta['properties']['executionBackend']['slug']
        tool_tag = db.query(ExampleTag).filter(
            ExampleTag.tag == f"tool:{backend_slug}"
        ).first()
        if tool_tag:
            tag_ids.append(tool_tag.id)

    return list(set(tag_ids))  # Remove duplicates
```

---

## 🧪 Phase 7: Testing

### 7.1 Unit Tests for Tag Model

**File:** `computor-backend/src/computor_backend/tests/test_example_tags.py`

```python
import pytest
from sqlalchemy.orm import Session
from computor_backend.model.example import ExampleTag, ExampleTagAssignment, Example

def test_create_tag(db: Session):
    """Test creating a new tag."""
    tag = ExampleTag(
        tag="domain:test",
        category="domain",
        value="test",
        title="Test Domain"
    )
    db.add(tag)
    db.commit()

    assert tag.id is not None
    assert tag.tag == "domain:test"
    assert tag.category == "domain"
    assert tag.value == "test"

def test_tag_unique_constraint(db: Session):
    """Test that duplicate tags are rejected."""
    tag1 = ExampleTag(tag="domain:test", category="domain", value="test")
    db.add(tag1)
    db.commit()

    tag2 = ExampleTag(tag="domain:test", category="domain", value="test")
    db.add(tag2)

    with pytest.raises(Exception):  # IntegrityError
        db.commit()

def test_tag_format_constraint(db: Session):
    """Test that invalid tag formats are rejected."""
    tag = ExampleTag(
        tag="INVALID_FORMAT",  # Should be category:value
        category="domain",
        value="test"
    )
    db.add(tag)

    with pytest.raises(Exception):  # CheckConstraint violation
        db.commit()

def test_hierarchical_tags(db: Session):
    """Test parent-child tag relationships."""
    parent = ExampleTag(
        tag="domain:mathematics",
        category="domain",
        value="mathematics"
    )
    db.add(parent)
    db.commit()

    child = ExampleTag(
        tag="topic:linear-algebra",
        category="topic",
        value="linear-algebra",
        parent_id=parent.id
    )
    db.add(child)
    db.commit()

    assert child.parent_id == parent.id
    assert child in parent.children
    assert child.parent == parent

def test_assign_tags_to_example(db: Session, example: Example):
    """Test assigning tags to an example."""
    tag1 = ExampleTag(tag="difficulty:beginner", category="difficulty", value="beginner")
    tag2 = ExampleTag(tag="tool:python", category="tool", value="python")
    db.add_all([tag1, tag2])
    db.commit()

    assignment1 = ExampleTagAssignment(example_id=example.id, tag_id=tag1.id)
    assignment2 = ExampleTagAssignment(example_id=example.id, tag_id=tag2.id)
    db.add_all([assignment1, assignment2])
    db.commit()

    db.refresh(example)
    assert len(example.tag_assignments) == 2
```

### 7.2 API Endpoint Tests

**File:** `computor-backend/src/computor_backend/tests/test_api_example_tags.py`

```python
from fastapi.testclient import TestClient

def test_list_tags(client: TestClient):
    """Test listing all tags."""
    response = client.get("/api/v1/example-tags")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_tags_by_category(client: TestClient):
    """Test filtering tags by category."""
    response = client.get("/api/v1/example-tags?category=domain")
    assert response.status_code == 200
    data = response.json()
    assert all(tag["category"] == "domain" for tag in data)

def test_create_tag_admin(client: TestClient, admin_token: str):
    """Test creating a tag as admin."""
    response = client.post(
        "/api/v1/example-tags",
        json={
            "tag": "custom:test-tag",
            "category": "custom",
            "value": "test-tag",
            "title": "Test Tag"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["tag"] == "custom:test-tag"

def test_create_tag_forbidden(client: TestClient, user_token: str):
    """Test that non-admin users cannot create tags."""
    response = client.post(
        "/api/v1/example-tags",
        json={
            "tag": "custom:test",
            "category": "custom",
            "value": "test"
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
```

---

## 📖 Phase 8: Documentation

### 8.1 Update README

Add section to main README:

```markdown
## Example Tag System

Examples can be tagged with structured, namespaced tags for advanced filtering and categorization.

### Tag Format

Tags use the format `category:value`:
- `domain:mathematics` - Mathematics domain
- `tool:python` - Python programming
- `difficulty:intermediate` - Intermediate difficulty level

### Available Tag Categories

- **domain**: Academic discipline (computer-science, mathematics, physics, etc.)
- **topic**: Specific subject matter (algorithms, linear-algebra, etc.)
- **difficulty**: Complexity level (beginner, intermediate, advanced, expert)
- **language**: Natural language (en, de, fr, es)
- **tool**: Programming languages and tools (python, matlab, java, git)
- **format**: Submission format (code, essay, quiz, presentation)
- **grading**: Assessment method (automated, manual, peer-review)
- **duration**: Time commitment (short, medium, long)
- **cognitive**: Bloom's taxonomy level (remember, understand, apply, analyze, evaluate, create)
- **strategy**: Teaching approach (tutorial, project-based, case-study)
- **skill**: Skills developed (problem-solving, debugging, critical-thinking)
- **accessibility**: Accessibility features (screen-reader, keyboard-only, captioned)
- **custom**: Institution-specific tags

### API Usage

```python
# List all tags
GET /api/v1/example-tags

# List tags by category
GET /api/v1/example-tags?category=domain

# List all categories
GET /api/v1/example-tags/categories

# Filter examples by tags
GET /api/v1/examples?tag_ids=<uuid1>,<uuid2>&difficulty_level=intermediate
```
```

### 8.2 API Documentation

Tags will automatically appear in OpenAPI/Swagger docs at `/docs`.

---

## ✅ Phase 9: Deployment Checklist

### Pre-Deployment

- [ ] Review all model changes
- [ ] Review migration script
- [ ] Test migration on development database
- [ ] Test rollback (downgrade)
- [ ] Review seeder script
- [ ] Run all unit tests
- [ ] Run all integration tests
- [ ] Update API documentation
- [ ] Review performance impact (indexes)

### Deployment Steps

1. **Backup database**
   ```bash
   pg_dump -h localhost -U postgres computor > backup_pre_tags_$(date +%Y%m%d).sql
   ```

2. **Run migration**
   ```bash
   cd computor-backend/src
   alembic upgrade head
   ```

3. **Seed tags**
   ```bash
   python computor_backend/scripts/seed_example_tags.py
   ```

4. **Verify**
   ```bash
   # Check tables created
   psql -U postgres -d computor -c "\dt example_tag*"

   # Check tags seeded
   psql -U postgres -d computor -c "SELECT COUNT(*) FROM example_tag;"
   ```

5. **Restart services**
   ```bash
   bash startup.sh
   ```

6. **Test API endpoints**
   ```bash
   curl http://localhost:8000/api/v1/example-tags
   curl http://localhost:8000/api/v1/example-tags/categories
   ```

### Post-Deployment

- [ ] Monitor database performance
- [ ] Check API response times
- [ ] Verify tag filtering works correctly
- [ ] Test tag creation/update/delete (admin only)
- [ ] Update frontend to use new tag system
- [ ] Migrate existing tags array data to new system (if applicable)

---

## 🔄 Phase 10: Migration Strategy for Existing Data

If you have existing examples with legacy `tags` array:

### 10.1 Create Migration Script

**File:** `computor-backend/src/computor_backend/scripts/migrate_legacy_tags.py`

```python
"""
Migrate legacy tags array to new tag system.
"""

from computor_backend.database import get_db
from computor_backend.model.example import Example, ExampleTag, ExampleTagAssignment

def migrate_legacy_tags():
    db = next(get_db())

    examples = db.query(Example).all()

    for example in examples:
        if not example.tags:
            continue

        print(f"Migrating tags for example: {example.title}")

        for legacy_tag in example.tags:
            # Try to parse as category:value
            if ':' in legacy_tag:
                category, value = legacy_tag.split(':', 1)
            else:
                # Assume it's a custom tag
                category = 'custom'
                value = legacy_tag

            # Find or create tag
            tag = db.query(ExampleTag).filter(
                ExampleTag.category == category,
                ExampleTag.value == value
            ).first()

            if not tag:
                tag = ExampleTag(
                    tag=f"{category}:{value}",
                    category=category,
                    value=value,
                    title=value.replace('-', ' ').title()
                )
                db.add(tag)
                db.flush()

            # Create assignment
            existing = db.query(ExampleTagAssignment).filter(
                ExampleTagAssignment.example_id == example.id,
                ExampleTagAssignment.tag_id == tag.id
            ).first()

            if not existing:
                assignment = ExampleTagAssignment(
                    example_id=example.id,
                    tag_id=tag.id
                )
                db.add(assignment)

        db.commit()

    print("Migration complete!")

if __name__ == "__main__":
    migrate_legacy_tags()
```

---

## 📊 Success Metrics

Track these metrics after deployment:

1. **Database Performance**
   - Query time for tag filtering
   - Index usage statistics
   - Table sizes

2. **API Performance**
   - Response times for `/api/v1/example-tags`
   - Response times for filtered `/api/v1/examples` queries

3. **Usage Statistics**
   - Number of tags created
   - Most used tags
   - Examples tagged vs untagged

4. **User Feedback**
   - Ease of finding examples
   - Tag relevance
   - Missing tag categories

---

## 🎯 Future Enhancements

### Phase 11 (Optional)

1. **Tag Analytics**
   - Track tag usage statistics
   - Popular tag combinations
   - Tag effectiveness metrics

2. **Auto-Tagging**
   - ML-based auto-tagging from meta.yaml
   - Suggest tags based on content
   - Bulk tag operations

3. **Tag Synonyms**
   - Map similar tags (e.g., "python" and "python3")
   - Tag aliases for different languages

4. **Tag Hierarchies UI**
   - Tree view of hierarchical tags
   - Drag-and-drop tag organization
   - Visual tag browser

5. **Advanced Filtering**
   - Boolean tag queries (AND, OR, NOT)
   - Weighted tag search
   - Similar examples by tag overlap

---

## 📚 References

- [PostgreSQL Array Functions](https://www.postgresql.org/docs/current/functions-array.html)
- [SQLAlchemy Relationship Patterns](https://docs.sqlalchemy.org/en/14/orm/basic_relationships.html)
- [FastAPI Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/)
- [Pydantic Models](https://docs.pydantic.dev/latest/)

---

## ✅ Sign-off

- [ ] Plan reviewed by: _______________
- [ ] Technical feasibility confirmed: _______________
- [ ] Database schema approved: _______________
- [ ] Migration strategy approved: _______________
- [ ] Ready for implementation: _______________

**Estimated Implementation Time:** 3-5 days

**Risk Level:** Medium (requires database migration and data model changes)

**Rollback Plan:** Alembic downgrade available; database backup required before deployment

---

*End of Implementation Plan*
