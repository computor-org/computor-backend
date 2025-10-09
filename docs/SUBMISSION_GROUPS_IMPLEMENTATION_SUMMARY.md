# Submission Groups Implementation Summary

**Date:** 2025-10-08
**Status:** Phase 1 Complete ✅ | Phase 2 Designed 📋

---

## Overview

This document summarizes the investigation, fixes, and design for the submission groups and student repository creation system.

## Part A: Individual Submissions (max_group_size=1) - ✅ COMPLETE

### Critical Issue Found

**Problem:** The `post_create` hook for `CourseMember` was commented out in [computor-types/src/computor_types/course_members.py](../computor-types/src/computor_types/course_members.py) during "Phase 4" refactoring but **NEVER migrated to the backend**.

**Impact:**
- ❌ Student repository creation workflow (`StudentRepositoryCreationWorkflow`) was never triggered
- ❌ Students joining courses did not get GitLab repositories
- ❌ Submission groups were only created lazily on first page access (pull-based)

### Fixes Implemented

#### 1. Added `post_create` Hook for CourseMember

**File:** [computor-backend/src/computor_backend/interfaces/course_member.py](../computor-backend/src/computor_backend/interfaces/course_member.py)

**What it does:**
- Automatically provisions submission groups for all individual assignments (max_group_size=1 or None) when student joins course
- Triggers `StudentRepositoryCreationWorkflow` to create GitLab repository
- Passes all submission group IDs to workflow for proper repository configuration

**Workflow:**
```
Student added to course (CourseMember created)
  ↓
post_create_course_member() runs
  ↓
provision_submission_groups_for_user() creates submission groups
  ↓
Query all submission groups for this student
  ↓
Trigger StudentRepositoryCreationWorkflow with submission_group_ids
  ↓
GitLab repository created and configured
```

#### 2. Added `post_create` Hook for CourseContent

**File:** [computor-backend/src/computor_backend/interfaces/course_content.py](../computor-backend/src/computor_backend/interfaces/course_content.py)

**What it does:**
- When a new individual assignment (max_group_size=1 or None) is created
- Automatically creates submission groups for all **existing** students in the course
- Ensures consistency: students don't miss assignments added after they joined

**Workflow:**
```
New individual assignment created (CourseContent)
  ↓
post_create_course_content() runs
  ↓
Check if submittable and max_group_size ≤ 1
  ↓
Get all students in course
  ↓
Create submission group + member for each student
  ↓
Students can now submit to new assignment
```

#### 3. Removed NotImplementedException

**Files:**
- [computor-backend/src/computor_backend/repositories/submission_group_provisioning.py](../computor-backend/src/computor_backend/repositories/submission_group_provisioning.py)
- [computor-backend/src/computor_backend/business_logic/submission_groups.py](../computor-backend/src/computor_backend/business_logic/submission_groups.py)

**Changes:**
- Replace `raise NotImplementedException` with graceful skip + log message
- Team assignments (max_group_size > 1) are now **skipped** rather than erroring
- Functions return `None` for team assignments that haven't been created yet

### Behavior Summary (Individual Assignments)

| Event | Old Behavior | New Behavior ✅ |
|-------|--------------|----------------|
| Student joins course | ❌ No submission groups<br>❌ No repository | ✅ Submission groups created<br>✅ Repository created via Temporal |
| New assignment created | ❌ Existing students have no groups | ✅ All students get submission groups |
| Student views assignment | ✅ Lazy creation (fallback) | ✅ Already exists (eager) |

---

## Part B: Team Submissions (max_group_size > 1) - 📋 DESIGNED

### Design Document

Full design: [TEAM_FORMATION_DESIGN.md](./TEAM_FORMATION_DESIGN.md)

### Key Design Decisions

#### 1. **Ruleset Storage: `CourseContent.properties.team_formation`**

Rules are **assignment-specific** and stored in JSONB:

```json
{
  "team_formation": {
    "mode": "hybrid",
    "max_group_size": 4,
    "min_group_size": 2,
    "formation_deadline": "2025-10-15T23:59:59Z",
    "allow_student_group_creation": true,
    "allow_student_join_groups": true,
    "lock_teams_at_deadline": true,
    "auto_assign_unmatched": false
  }
}
```

#### 2. **Three Formation Modes**

| Mode | Description | Use Case |
|------|-------------|----------|
| **instructor_predefined** | Instructor creates all teams | Labs with fixed partnerships |
| **self_organized** | Students create/join teams | Open projects |
| **hybrid** | Both allowed | Flexible courses |

#### 3. **Team Lifecycle States**

```
forming → locked → archived
  ↓         ↓
  (deadline or manual)
  (repository creation)
```

### API Endpoints (To Be Implemented)

#### Student Endpoints
```
POST   /course-contents/{id}/submission-groups/my-team
GET    /course-contents/{id}/submission-groups/my-team
DELETE /course-contents/{id}/submission-groups/my-team
GET    /course-contents/{id}/submission-groups/available
POST   /submission-groups/{id}/join
DELETE /submission-groups/{id}/leave
```

#### Instructor Endpoints
```
POST   /course-contents/{id}/submission-groups  (with member_ids)
PUT    /submission-groups/{id}/members
POST   /submission-groups/{id}/lock
```

### Implementation Phases

**Phase 2A:** Core Team Management (Week 1)
- ✅ NotImplementedException removed
- ⏳ Validation helpers
- ⏳ Student endpoints (create, view, delete team)

**Phase 2B:** Team Discovery (Week 2)
- ⏳ Browse available teams
- ⏳ Join/leave endpoints
- ⏳ Join codes (optional)

**Phase 2C:** Deadline & Repository (Week 3)
- ⏳ Deadline enforcement (Temporal job)
- ⏳ Team locking logic
- ⏳ Trigger `StudentRepositoryCreationWorkflow` with `is_team=True`
- ⏳ Auto-assignment algorithm

**Phase 2D:** Frontend UI (Week 4)
- ⏳ Team browser component
- ⏳ Team creation dialog
- ⏳ Member management UI

---

## Testing Recommendations

### Phase 1 Testing (Individual Assignments)

**Test 1: New Student Joins Course**
```
1. Create course with 2 individual assignments (max_group_size=1)
2. Add student to course
3. Verify:
   - 2 submission groups created
   - Temporal workflow triggered
   - GitLab repository created
```

**Test 2: New Assignment Created**
```
1. Course has 5 students
2. Create new individual assignment
3. Verify:
   - 5 submission groups created (one per student)
   - Students can view assignment immediately
```

**Test 3: Team Assignment (Graceful Handling)**
```
1. Create team assignment (max_group_size=4)
2. Add student to course
3. Verify:
   - No submission group auto-created
   - No error raised
   - Student sees "team not formed" message (future UI)
```

### Phase 2 Testing (Team Assignments)

Will be defined during Phase 2 implementation.

---

## Migration Notes

### No Database Migration Required! ✅

All changes use existing tables and JSONB properties:
- `CourseContent.properties` for team formation rules
- `CourseContent.max_group_size` for team size limits
- `SubmissionGroup` and `SubmissionGroupMember` (no schema changes)

### Backward Compatibility

- ✅ Existing individual assignments work unchanged
- ✅ No breaking changes to existing APIs
- ✅ Lazy provisioning still works as fallback
- ✅ Existing course members will get submission groups on next course content view (or retroactively via script)

### Deployment Steps

1. Deploy backend changes
2. Restart Temporal workers (to pick up updated workflow triggers)
3. Verify logs for `post_create` hooks firing
4. Optional: Run backfill script for existing course members

**Backfill Script Example:**
```python
# For all existing course members without submission groups
for course_member in CourseMember.query.all():
    provision_submission_groups_for_user(
        course_member.user_id,
        course_member.course_id,
        db
    )
    trigger_repository_workflow(course_member)
```

---

## Key Files Modified

### Phase 1 Implementation
1. [computor-backend/src/computor_backend/interfaces/course_member.py](../computor-backend/src/computor_backend/interfaces/course_member.py) - Added `post_create` hook
2. [computor-backend/src/computor_backend/interfaces/course_content.py](../computor-backend/src/computor_backend/interfaces/course_content.py) - Added `post_create` hook
3. [computor-backend/src/computor_backend/repositories/submission_group_provisioning.py](../computor-backend/src/computor_backend/repositories/submission_group_provisioning.py) - Removed `NotImplementedException`
4. [computor-backend/src/computor_backend/business_logic/submission_groups.py](../computor-backend/src/computor_backend/business_logic/submission_groups.py) - Removed `NotImplementedException`

### Phase 2 Design Documents
1. [docs/TEAM_FORMATION_DESIGN.md](./TEAM_FORMATION_DESIGN.md) - Complete team formation design

### Untouched (Working as Expected)
- [computor-backend/src/computor_backend/tasks/temporal_student_repository.py](../computor-backend/src/computor_backend/tasks/temporal_student_repository.py) - Workflow exists and works
- [computor-backend/src/computor_backend/repositories/student_view.py](../computor-backend/src/computor_backend/repositories/student_view.py) - Lazy provisioning (fallback)

---

## Summary

### What Was Broken
- ❌ Student repository creation never triggered
- ❌ CourseMember post_create logic lost in refactoring
- ❌ NotImplementedException blocked team assignments
- ❌ Submission groups only created reactively (lazy)

### What's Fixed (Phase 1)
- ✅ CourseMember post_create hook implemented
- ✅ CourseContent post_create hook implemented
- ✅ StudentRepositoryCreationWorkflow triggered automatically
- ✅ Eager submission group provisioning
- ✅ Team assignments gracefully skipped (no errors)

### What's Next (Phase 2)
- ⏳ Team formation endpoints
- ⏳ Team discovery and joining
- ⏳ Deadline enforcement
- ⏳ Team repository creation
- ⏳ Frontend UI components

---

**Questions or Issues?** Contact the team or see [TEAM_FORMATION_DESIGN.md](./TEAM_FORMATION_DESIGN.md) for detailed design.
