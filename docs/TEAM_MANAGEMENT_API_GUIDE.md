# Team Management API Guide

**Version:** Phase 2A Complete
**Last Updated:** 2025-10-08

---

## Overview

The Team Management API allows students to create, join, and leave teams for group assignments. Instructors can configure team formation rules at both the course level (defaults) and course_content level (per-assignment overrides).

## Quick Start

### 1. Configure Team Formation Rules

**Course-level defaults** (applies to all assignments):

```http
PATCH /courses/{course_id}
Content-Type: application/json

{
  "properties": {
    "team_formation": {
      "mode": "hybrid",
      "max_group_size": 3,
      "allow_student_group_creation": true,
      "formation_deadline_offset": "1 week before due"
    }
  }
}
```

**Assignment-level override** (final project allows teams of 5):

```http
PATCH /course-contents/{course_content_id}
Content-Type: application/json

{
  "max_group_size": 5,
  "properties": {
    "team_formation": {
      "max_group_size": 5,
      "formation_deadline": "2025-12-01T23:59:59Z"
    }
  }
}
```

### 2. Student Creates a Team

```http
POST /course-contents/{course_content_id}/submission-groups/my-team
Authorization: Bearer <student_token>
Content-Type: application/json

{
  "team_name": "Team Awesome"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "course_content_id": "uuid",
  "course_id": "uuid",
  "max_group_size": 4,
  "status": "forming",
  "created_by": "student",
  "join_code": "A3F9E2",
  "members": [
    {
      "course_member_id": "uuid",
      "user_id": "uuid",
      "given_name": "Alice",
      "family_name": "Smith",
      "email": "alice@university.edu"
    }
  ],
  "member_count": 1,
  "can_join": true,
  "locked_at": null
}
```

### 3. Browse Available Teams

```http
GET /course-contents/{course_content_id}/submission-groups/available
Authorization: Bearer <student_token>
```

**Response 200:**
```json
[
  {
    "id": "team-uuid-1",
    "member_count": 2,
    "max_group_size": 4,
    "join_code": "A3F9E2",
    "requires_approval": false,
    "status": "forming",
    "members": [
      {"given_name": "Alice", "family_name": "Smith"},
      {"given_name": "Bob", "family_name": "Jones"}
    ]
  },
  {
    "id": "team-uuid-2",
    "member_count": 1,
    "max_group_size": 4,
    "join_code": "B4E8C1",
    "requires_approval": false,
    "status": "forming",
    "members": [
      {"given_name": "Charlie", "family_name": "Brown"}
    ]
  }
]
```

### 4. Join a Team

```http
POST /submission-groups/{submission_group_id}/join
Authorization: Bearer <student_token>
Content-Type: application/json

{
  "join_code": "A3F9E2"
}
```

**Response 200:**
```json
{
  "id": "team-uuid-1",
  "status": "joined",
  "message": "You have successfully joined the team (3/4 members)"
}
```

### 5. View My Team

```http
GET /course-contents/{course_content_id}/submission-groups/my-team
Authorization: Bearer <student_token>
```

**Response 200:** (Same as create team response)

### 6. Leave Team

```http
DELETE /course-contents/{course_content_id}/submission-groups/my-team
Authorization: Bearer <student_token>
```

**Response 200:**
```json
{
  "success": true,
  "message": "You left the team. 2 member(s) remaining."
}
```

OR if last member:

```json
{
  "success": true,
  "message": "You left the team and the team was deleted (no remaining members)"
}
```

---

## Endpoints Reference

### Student Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/course-contents/{id}/submission-groups/my-team` | Create a new team |
| `GET` | `/course-contents/{id}/submission-groups/my-team` | Get your team |
| `DELETE` | `/course-contents/{id}/submission-groups/my-team` | Leave your team |
| `GET` | `/course-contents/{id}/submission-groups/available` | Browse teams to join |
| `POST` | `/submission-groups/{id}/join` | Join a team |

### Instructor Endpoints (Standard CRUD)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/submission-groups` | Create predefined team |
| `GET` | `/submission-groups?course_content_id={id}` | List all teams |
| `GET` | `/submission-groups/{id}` | Get team details |
| `PUT` | `/submission-groups/{id}` | Update team |
| `DELETE` | `/submission-groups/{id}` | Delete team |

---

## Team Formation Rules Schema

### Course-Level Defaults

Store in `Course.properties.team_formation`:

```json
{
  "team_formation": {
    "mode": "self_organized | instructor_predefined | hybrid",
    "max_group_size": 3,
    "min_group_size": 1,
    "formation_deadline_offset": "1 week before due",
    "allow_student_group_creation": true,
    "allow_student_join_groups": true,
    "allow_student_leave_groups": true,
    "auto_assign_unmatched": false,
    "lock_teams_at_deadline": true,
    "require_approval": false
  }
}
```

### CourseContent-Level Overrides

Store in `CourseContent.properties.team_formation`:

```json
{
  "team_formation": {
    "max_group_size": 5,
    "formation_deadline": "2025-12-01T23:59:59Z"
  }
}
```

**Note:** Only non-null fields in `CourseContent.properties.team_formation` override course defaults. Missing fields inherit from course.

### Rule Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | enum | `"self_organized"` | `self_organized`, `instructor_predefined`, or `hybrid` |
| `max_group_size` | int | From `CourseContent.max_group_size` | Maximum team size |
| `min_group_size` | int | `1` | Minimum team size (validation) |
| `formation_deadline` | ISO datetime | `null` | Absolute deadline (ISO 8601) |
| `formation_deadline_offset` | string | `null` | Relative deadline (e.g., "1 week before due") |
| `allow_student_group_creation` | bool | `true` | Students can create teams |
| `allow_student_join_groups` | bool | `true` | Students can join existing teams |
| `allow_student_leave_groups` | bool | `true` | Students can leave teams |
| `auto_assign_unmatched` | bool | `false` | Auto-assign solo students at deadline |
| `lock_teams_at_deadline` | bool | `true` | Lock teams at deadline |
| `require_approval` | bool | `false` | Team creator approves joins (Phase 2B) |

---

## Validation Rules

### Creating a Team

✅ **Allowed when:**
- `allow_student_group_creation` is `true`
- Student is not already in a team for this course content
- Formation deadline has not passed
- `max_group_size > 1` (team assignment)

❌ **Blocked when:**
- Student already has a team
- Deadline passed
- Assignment is individual (`max_group_size = 1`)
- Team creation disabled by instructor

### Joining a Team

✅ **Allowed when:**
- `allow_student_join_groups` is `true`
- Student is not already in a team
- Team is in `forming` status (not locked)
- Team is not full (`member_count < max_group_size`)
- Formation deadline has not passed

❌ **Blocked when:**
- Student already has a team
- Team is locked or full
- Deadline passed
- Joining disabled by instructor

### Leaving a Team

✅ **Allowed when:**
- `allow_student_leave_groups` is `true`
- Formation deadline has not passed
- Team is in `forming` status (not locked)

❌ **Blocked when:**
- Team is locked
- Deadline passed
- Leaving disabled by instructor

**Special behavior:**
- If last member leaves → team is automatically deleted

---

## Error Responses

### 400 Bad Request

**Scenario: Not a team assignment**
```json
{
  "detail": "Course content 'Assignment 1' is not a team assignment (max_group_size=1)"
}
```

**Scenario: Already has a team**
```json
{
  "detail": "You already have a team for this assignment (team abc123)"
}
```

**Scenario: Deadline passed**
```json
{
  "detail": "Team formation deadline has passed (2025-11-15T23:59:59Z)"
}
```

### 403 Forbidden

**Scenario: Not a course member**
```json
{
  "detail": "You are not a member of course xyz789"
}
```

### 404 Not Found

**Scenario: No team yet**
```json
{
  "detail": "You don't have a team for this assignment yet"
}
```

**Scenario: Team not found**
```json
{
  "detail": "Team abc123 not found"
}
```

---

## Use Case Examples

### Use Case 1: Self-Organized Teams (Most Common)

**Instructor Setup:**
```json
// Course defaults
{
  "mode": "self_organized",
  "max_group_size": 4,
  "formation_deadline_offset": "1 week before due",
  "allow_student_group_creation": true,
  "lock_teams_at_deadline": true
}
```

**Student Workflow:**
1. Alice creates "Team Awesome" → Gets join code `A3F9E2`
2. Alice shares code with Bob and Charlie
3. Bob joins using join code
4. Charlie joins using join code
5. Team has 3/4 members (can still accept 1 more)
6. Deadline passes → Team locked → Repository created

### Use Case 2: Instructor Pre-Defined Teams

**Instructor Setup:**
```json
{
  "mode": "instructor_predefined",
  "max_group_size": 3,
  "allow_student_group_creation": false,
  "allow_student_join_groups": false
}
```

**Instructor Actions:**
1. Create Team 1: `POST /submission-groups` with `member_ids: [alice, bob, charlie]`
2. Create Team 2: `POST /submission-groups` with `member_ids: [dave, eve, frank]`
3. Teams auto-locked (status: `locked`)
4. Repositories created immediately

**Student Experience:**
- Cannot create teams
- Cannot join/leave teams
- See assigned team only

### Use Case 3: Hybrid (Flexible)

**Instructor Setup:**
```json
{
  "mode": "hybrid",
  "max_group_size": 4,
  "formation_deadline": "2025-11-20T23:59:59Z",
  "allow_student_group_creation": true,
  "auto_assign_unmatched": true
}
```

**Workflow:**
1. Instructor creates 2 predefined teams (for students with accommodations)
2. Other students create/join teams freely
3. At deadline (Nov 20):
   - Lock all teams
   - Auto-assign solo students to teams with space
   - Create repositories for all teams

### Use Case 4: Per-Assignment Override

**Course Default: Individual work**
```json
// Course.properties.team_formation
{
  "max_group_size": 1,
  "allow_student_group_creation": false
}
```

**Final Project: Allow teams**
```json
// CourseContent.properties.team_formation (Final Project)
{
  "max_group_size": 5,
  "mode": "self_organized",
  "allow_student_group_creation": true,
  "formation_deadline": "2025-12-01T23:59:59Z"
}
```

**Result:**
- Assignments 1-9: Individual (inherit course defaults)
- Final Project: Teams of up to 5 allowed

---

## Future Enhancements (Phase 2B+)

### Phase 2B: Approval Workflow
- `require_approval: true` → Join requests need team creator approval
- New endpoints:
  - `GET /submission-groups/{id}/join-requests`
  - `POST /submission-groups/{id}/join-requests/{request_id}/approve`
  - `POST /submission-groups/{id}/join-requests/{request_id}/reject`

### Phase 2C: Deadline Enforcement
- Background Temporal workflow runs at `formation_deadline`
- Locks all teams (`status: forming → locked`)
- Auto-assigns unmatched students (if `auto_assign_unmatched: true`)
- Triggers `StudentRepositoryCreationWorkflow` with `is_team: true`

### Phase 2D: Team Invitations
- Team creators can send invite links
- Direct invite by email or username
- Notification system integration

---

## Testing

### Manual Testing Checklist

#### Happy Path
- [ ] Create team for team assignment
- [ ] Browse available teams
- [ ] Join a team with space
- [ ] Leave team before deadline
- [ ] Get my team info

#### Error Cases
- [ ] Try to create team for individual assignment → 400
- [ ] Try to create team when already in team → 400
- [ ] Try to join full team → 400
- [ ] Try to leave locked team → 400
- [ ] Try to join team when already in team → 400

#### Inheritance
- [ ] Set course defaults, verify inherited by assignment
- [ ] Override assignment rules, verify course defaults still apply for other fields
- [ ] Create assignment with only partial override

### cURL Examples

**Create Team:**
```bash
curl -X POST http://localhost:8000/course-contents/{id}/submission-groups/my-team \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"team_name": "Team Awesome"}'
```

**Browse Teams:**
```bash
curl http://localhost:8000/course-contents/{id}/submission-groups/available \
  -H "Authorization: Bearer $TOKEN"
```

**Join Team:**
```bash
curl -X POST http://localhost:8000/submission-groups/{team_id}/join \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"join_code": "A3F9E2"}'
```

---

## Troubleshooting

### Issue: "You already have a team"

**Cause:** Student is already in a team for this course content.

**Solution:**
1. Leave current team first: `DELETE /course-contents/{id}/submission-groups/my-team`
2. Then create/join new team

### Issue: "Team formation deadline has passed"

**Cause:** Assignment's `formation_deadline` is in the past.

**Solution:**
1. Instructor extends deadline: Update `CourseContent.properties.team_formation.formation_deadline`
2. Or unlock team: Update `SubmissionGroup.properties.team_formation.status` to `forming`

### Issue: "Not a team assignment"

**Cause:** `CourseContent.max_group_size` is 1 or None.

**Solution:**
1. Update `CourseContent.max_group_size` to value > 1
2. Ensure `CourseContentKind.submittable` is `true`

---

## Database Schema

**No schema changes required!** Uses existing tables:

- `Course.properties` → Course-level team formation defaults
- `CourseContent.properties` → Assignment-level overrides
- `CourseContent.max_group_size` → Team size limit
- `SubmissionGroup` → Represents a team
- `SubmissionGroup.properties.team_formation` → Team status, join code, metadata
- `SubmissionGroupMember` → Team membership

---

## Security Considerations

- ✅ Students can only create/join teams in courses they're enrolled in
- ✅ Students can only view teams for assignments in their courses
- ✅ Instructors can view all teams
- ✅ Join codes are random 6-character hex (16.7M possibilities)
- ✅ Deadline enforcement prevents late team changes
- ✅ Locked teams cannot be modified by students

---

**For questions or issues, see [TEAM_FORMATION_DESIGN.md](./TEAM_FORMATION_DESIGN.md) for detailed design.**
