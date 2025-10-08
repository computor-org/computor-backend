# Team Formation System Design

## Overview

This document describes the hybrid team formation system that allows instructors to define rules and students to self-organize into teams for group assignments.

## Architecture

### 1. Ruleset Storage Location - INHERITANCE PATTERN ✨

**Decision: Two-level inheritance with `Course.properties` defaults and `CourseContent.properties` overrides**

**How it works:**
```
Course.properties.team_formation (defaults for all assignments)
  ↓
CourseContent.properties.team_formation (per-assignment overrides)
  ↓
Resolved rules = Course defaults + CourseContent overrides
```

**Resolution logic:**
```python
def get_team_formation_rules(course_content: CourseContent, course: Course):
    """
    Get team formation rules with inheritance:
    - Start with course-level defaults
    - Override with course_content-level rules (if field is not None)
    - Field-level granularity (not all-or-nothing)
    """
    # Start with course-level defaults
    course_rules = course.properties.get('team_formation', {}) if course.properties else {}

    # Get course_content-level overrides
    content_rules = course_content.properties.get('team_formation', {}) if course_content.properties else {}

    # Merge: content_rules override course_rules (field by field)
    # Only non-None values in content_rules override course defaults
    resolved = {**course_rules}  # Start with course defaults
    for key, value in content_rules.items():
        if value is not None:  # Only override if explicitly set
            resolved[key] = value

    return resolved
```

**Rationale:**
- ✅ **Consistency**: Set defaults once at course level, apply to all assignments
- ✅ **Flexibility**: Override per-assignment when needed (e.g., final project allows teams)
- ✅ **DRY**: Don't repeat same rules for every assignment
- ✅ **No migration**: Uses existing JSONB columns in `Course` and `CourseContent`
- ✅ **Granular**: Can override individual fields (e.g., only change deadline, keep other rules)

**Example Use Cases:**

**Use Case 1: All assignments individual except final project**
```json
// Course.properties.team_formation (default for all assignments)
{
  "mode": "instructor_predefined",
  "max_group_size": 1,
  "allow_student_group_creation": false
}

// Assignment 1, 2, 3: Inherit course defaults → individual work

// Final Project: CourseContent.properties.team_formation (overrides)
{
  "max_group_size": 4,
  "mode": "hybrid",
  "allow_student_group_creation": true,
  "formation_deadline": "2025-12-01T23:59:59Z"
}
// Resolved: max_group_size=4, mode=hybrid, allow_student_group_creation=true, formation_deadline set
```

**Use Case 2: Course allows teams by default, but midterm must be individual**
```json
// Course.properties.team_formation (default - teams allowed)
{
  "mode": "hybrid",
  "max_group_size": 3,
  "formation_deadline_offset": "1 week before due",
  "allow_student_group_creation": true,
  "lock_teams_at_deadline": true
}

// Labs 1-5: Inherit course defaults → teams of 3 allowed

// Midterm Exam: CourseContent.properties.team_formation (overrides)
{
  "max_group_size": 1,
  "mode": "instructor_predefined",
  "allow_student_group_creation": false
}
// Resolved: Individual work (max_group_size=1), no student team creation
```

**Use Case 3: Partial override (only change deadline for one assignment)**
```json
// Course.properties.team_formation
{
  "mode": "self_organized",
  "max_group_size": 2,
  "formation_deadline_offset": "1 week before due",
  "lock_teams_at_deadline": true
}

// Assignment 3 needs longer team formation time:
// CourseContent.properties.team_formation
{
  "formation_deadline": "2025-11-15T23:59:59Z"  // Only override deadline
}
// Resolved: All course defaults + custom deadline for this assignment
```

### 2. Team Formation Rules Schema

Rules are stored in `CourseContent.properties.team_formation`:

```json
{
  "team_formation": {
    "mode": "self_organized | instructor_predefined | hybrid",
    "max_group_size": 4,
    "min_group_size": 2,
    "formation_deadline": "2025-10-15T23:59:59Z",
    "allow_student_group_creation": true,
    "allow_student_join_groups": true,
    "allow_student_leave_groups": true,
    "auto_assign_unmatched": false,
    "lock_teams_at_deadline": true,
    "require_approval": false
  }
}
```

#### Rule Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | enum | `"self_organized"` | `self_organized`: Students create/join teams<br>`instructor_predefined`: Instructor creates all teams<br>`hybrid`: Both allowed |
| `max_group_size` | int | From `CourseContent.max_group_size` | Maximum team size |
| `min_group_size` | int | `1` | Minimum team size (for validation) |
| `formation_deadline` | ISO datetime | `null` | Deadline for team formation (ISO 8601) |
| `allow_student_group_creation` | bool | `true` | Students can create new teams |
| `allow_student_join_groups` | bool | `true` | Students can join existing teams |
| `allow_student_leave_groups` | bool | `true` | Students can leave teams before deadline |
| `auto_assign_unmatched` | bool | `false` | Automatically assign solo students to teams at deadline |
| `lock_teams_at_deadline` | bool | `true` | Lock team membership after deadline |
| `require_approval` | bool | `false` | Team creator must approve join requests |

### 3. Database Schema

**No schema changes required!** Using existing tables:

- `CourseContent.max_group_size` - Team size limit
- `CourseContent.properties` - Team formation rules
- `SubmissionGroup` - Represents a team
- `SubmissionGroupMember` - Team membership

**New field in `SubmissionGroup.properties`:**
```json
{
  "team_formation": {
    "status": "forming | locked | archived",
    "created_by": "student | instructor | system",
    "locked_at": "2025-10-15T23:59:59Z",
    "join_code": "ABC123"  // Optional: for easy joining
  }
}
```

### 4. API Endpoints

#### 4.1 Student Team Management

```
POST   /course-contents/{id}/submission-groups/my-team
GET    /course-contents/{id}/submission-groups/my-team
DELETE /course-contents/{id}/submission-groups/my-team
```

**Create Team:**
```http
POST /course-contents/{course_content_id}/submission-groups/my-team
Content-Type: application/json

{
  "team_name": "Team Awesome"  // Optional
}

Response 201:
{
  "id": "uuid",
  "course_content_id": "uuid",
  "max_group_size": 4,
  "join_code": "ABC123",
  "members": [
    {
      "course_member_id": "uuid",
      "user": { "given_name": "Alice", "family_name": "Smith" }
    }
  ]
}
```

#### 4.2 Team Discovery & Joining

```
GET    /course-contents/{id}/submission-groups/available
POST   /submission-groups/{id}/join
DELETE /submission-groups/{id}/leave
```

**Browse Available Teams:**
```http
GET /course-contents/{course_content_id}/submission-groups/available

Response 200:
[
  {
    "id": "uuid",
    "member_count": 2,
    "max_group_size": 4,
    "join_code": "ABC123",
    "requires_approval": false,
    "members": [
      { "given_name": "Alice" },
      { "given_name": "Bob" }
    ]
  }
]
```

**Join Team:**
```http
POST /submission-groups/{submission_group_id}/join

Response 200 (immediate join):
{
  "id": "uuid",
  "status": "joined"
}

Response 202 (pending approval):
{
  "id": "uuid",
  "status": "pending_approval"
}
```

**Leave Team:**
```http
DELETE /submission-groups/{submission_group_id}/leave

Response 204: No Content
```

#### 4.3 Instructor Team Management

```
POST   /course-contents/{id}/submission-groups  (existing - with team creation)
GET    /course-contents/{id}/submission-groups  (existing)
PUT    /submission-groups/{id}/members          (new - bulk update)
DELETE /submission-groups/{id}                  (existing)
POST   /submission-groups/{id}/lock             (new - lock team)
```

**Create Predefined Team:**
```http
POST /course-contents/{course_content_id}/submission-groups
Content-Type: application/json

{
  "course_member_ids": ["uuid1", "uuid2", "uuid3"],
  "properties": {
    "team_formation": {
      "created_by": "instructor",
      "status": "locked"  // Locked by default for instructor-created
    }
  }
}
```

### 5. Business Logic & Validation

#### 5.1 Validation Rules

**When student creates team:**
1. ✅ `allow_student_group_creation` must be `true`
2. ✅ Student not already in a team for this course content
3. ✅ Formation deadline not passed (if set)
4. ✅ CourseContent has `max_group_size > 1`

**When student joins team:**
1. ✅ `allow_student_join_groups` must be `true`
2. ✅ Student not already in a team for this course content
3. ✅ Team not full (`member_count < max_group_size`)
4. ✅ Formation deadline not passed
5. ✅ Team not locked

**When student leaves team:**
1. ✅ `allow_student_leave_groups` must be `true`
2. ✅ Formation deadline not passed
3. ✅ Team not locked
4. ⚠️  If last member leaves, delete team (or archive)

#### 5.2 Deadline Enforcement

**Background job runs at deadline:**
1. Lock all teams for the course content
2. If `auto_assign_unmatched=true`:
   - Find solo students
   - Assign to teams with space
   - Create new teams if needed
3. Update `SubmissionGroup.properties.team_formation.status = "locked"`

#### 5.3 Repository Creation Trigger

**When to trigger `StudentRepositoryCreationWorkflow` with `is_team=True`?**

**Option 1: At team lock time** (RECOMMENDED)
- When team is manually locked by instructor
- When deadline passes and `lock_teams_at_deadline=true`
- Ensures all members are finalized before repo creation

**Option 2: When team reaches max_group_size**
- Immediate creation when full
- Risk: Members might leave/change

**Option 3: On first submission attempt**
- Lazy creation
- Risk: Delays, potential GitLab issues during submission

### 6. Implementation Phases

#### Phase 2A: Core Team Management (Week 1)

**Tasks:**
1. ✅ Remove `NotImplementedException` from submission group provisioning
2. ✅ Add validation helper: `validate_team_formation_rules()`
3. ✅ Implement student endpoints:
   - `POST /course-contents/{id}/submission-groups/my-team`
   - `GET /course-contents/{id}/submission-groups/my-team`
   - `DELETE /course-contents/{id}/submission-groups/my-team`
4. ✅ Add team membership validation logic
5. ✅ Update `post_create_course_content` to skip team assignments

#### Phase 2B: Team Discovery & Joining (Week 2)

**Tasks:**
1. ✅ Implement team discovery endpoint
2. ✅ Implement join/leave endpoints
3. ✅ Add join code generation (optional)
4. ✅ Add approval workflow (if `require_approval=true`)

#### Phase 2C: Deadline & Repository Creation (Week 3)

**Tasks:**
1. ✅ Create deadline enforcement background job (Temporal workflow)
2. ✅ Implement team locking logic
3. ✅ Trigger `StudentRepositoryCreationWorkflow` for teams
4. ✅ Add auto-assignment algorithm

#### Phase 2D: Frontend UI (Week 4)

**Tasks:**
1. ✅ Team browser component
2. ✅ Team creation dialog
3. ✅ Team member list/management
4. ✅ Join/leave buttons with confirmation

### 7. Example Workflows

#### Workflow 1: Self-Organized Teams

**Instructor setup:**
```json
// CourseContent.properties.team_formation
{
  "mode": "self_organized",
  "max_group_size": 4,
  "min_group_size": 2,
  "formation_deadline": "2025-10-20T23:59:59Z",
  "allow_student_group_creation": true,
  "allow_student_join_groups": true,
  "lock_teams_at_deadline": true
}
```

**Student actions:**
1. Alice creates team "Team Awesome"
2. Bob browses available teams, joins "Team Awesome"
3. Charlie joins "Team Awesome"
4. Team has 3 members (within 2-4 range)
5. Deadline passes → Team locked → GitLab repo created

#### Workflow 2: Instructor Predefined

**Instructor setup:**
```json
{
  "mode": "instructor_predefined",
  "max_group_size": 3,
  "allow_student_group_creation": false,
  "allow_student_join_groups": false
}
```

**Instructor actions:**
1. Create Team A: [Alice, Bob, Charlie]
2. Create Team B: [David, Eve, Frank]
3. Teams locked immediately
4. Trigger repo creation manually or at assignment start

#### Workflow 3: Hybrid

**Instructor setup:**
```json
{
  "mode": "hybrid",
  "max_group_size": 4,
  "formation_deadline": "2025-10-20T23:59:59Z",
  "allow_student_group_creation": true,
  "auto_assign_unmatched": true
}
```

**Combined actions:**
1. Instructor creates 2 predefined teams (locked)
2. Students create/join additional teams
3. At deadline: Auto-assign solo students to teams with space
4. Lock all teams → Create repos

## Migration Notes

**No database migration required!**

Existing code changes:
1. ✅ Remove `NotImplementedException` in:
   - `submission_group_provisioning.py:70-73`
   - `submission_groups.py:61-66`
2. ✅ Add team formation validation helpers
3. ✅ Add new API endpoints
4. ✅ Update workflow triggers

## Testing Strategy

### Unit Tests
- ✅ Validation rules for each scenario
- ✅ Team size enforcement
- ✅ Deadline checking
- ✅ Permission checks

### Integration Tests
- ✅ Student creates → joins → leaves team
- ✅ Instructor creates predefined teams
- ✅ Deadline enforcement job
- ✅ Repository creation for teams
- ✅ Auto-assignment algorithm

### Manual Testing
- ✅ UI workflows
- ✅ GitLab integration
- ✅ Error handling and edge cases

## Future Enhancements

1. **Team invitations** - Send invite links to specific students
2. **Team chat** - Integrate messaging for team coordination
3. **Team analytics** - Formation status dashboard for instructors
4. **Smart matching** - Algorithm to suggest compatible teammates
5. **Team templates** - Reuse team composition across assignments
6. **Cross-course teams** - Allow teams from previous courses

## Questions for Discussion

1. **Should we allow students to see other teams' members before joining?**
   - Privacy concerns vs transparency for finding friends

2. **What happens to submissions if a team member leaves after lock?**
   - Transfer ownership? Delete? Mark as incomplete?

3. **Should there be a minimum deadline lead time?**
   - e.g., "Teams must be formed at least 3 days before assignment due date"

4. **How to handle dropped students in locked teams?**
   - Auto-remove from team? Leave as inactive member?

---

**Status:** Design complete, ready for implementation approval
**Last Updated:** 2025-10-08
**Author:** Claude + User
