# Frontend Role-Based View Findings

## Context
The current frontend refactor focuses on expanding beyond the existing admin-only experience. We need dedicated lecturer, tutor, and student surfaces that only appear when the logged-in principal actually has the corresponding course role.

## Observations
- **Navigation model locked to admin/global** (`frontend/src/types/navigation.ts`, `frontend/src/utils/navigationConfig.ts`) – sidebar contexts are limited to `'global' | 'course' | 'admin'`, and the menu still exposes placeholder "Example" links.
- **Hard-coded context switching** (`frontend/src/app/components/AuthenticatedTopBarMenu.tsx`) – the top-bar menu toggles a single demo course (`courseId: '1'`) and cannot reflect actual course assignments, so role sections cannot be hidden when the user lacks access.
- **Routes missing for non-admin roles** (`frontend/src/app/routes/AppRoutes.tsx`) – only admin dashboards and shared dashboards are registered; there are no lecturer, tutor, or student pages to point navigation items at.
- **Role information flattened in auth services** (`frontend/src/services/basicAuthService.ts`, `frontend/src/services/ssoAuthService.ts`) – both services collapse roles to `'admin' | 'lecturer' | 'student'`, discarding tutor/owner claims and per-course assignments returned by `/auth/me`.
- **Backend already exposes scoped course APIs**:
  - Lecturers: `/lecturers/courses` & `/lecturers/courses/{course_id}` (`src/ctutor_backend/api/lecturer.py`)
  - Tutors: `/tutors/courses`, `/tutors/course-members`, graded content helpers (`src/ctutor_backend/api/tutor.py`)
  - Students: `/students/courses`, `/students/course-contents`, submissions (`src/ctutor_backend/api/students.py`)
  These endpoints enforce course-role checks via `check_course_permissions`, so they can drive frontend availability.

## Recommended Direction
1. **Bootstrap role access after login**
   - Extend `AuthUser` to include raw role claims and a map of courses by role.
   - After `/auth/me`, call role-specific endpoints (`/lecturers/courses`, `/tutors/courses`, `/students/courses`) to populate the map.
2. **Refactor navigation contexts**
   - Introduce `lecturer`, `tutor`, and `student` sidebar configurations alongside `admin`.
   - Remove placeholder links; derive permissions per menu item from the role/course metadata.
3. **Dynamic context switching**
   - Replace the hard-coded selections in `AuthenticatedTopBarMenu` with entries generated from the course-role map (e.g., "Tutor • Software Engineering WS25").
   - Updating the sidebar context should include `type`, `courseId`, `courseName`, and role-derived permissions.
4. **Add role-specific routes and pages**
   - Provide lecturer pages for course overviews/content management, tutor dashboards for grading queues, and student dashboards for assignments/submissions using the generated API clients (`frontend/src/api/generated`).
5. **Permission gating utility**
   - Centralize mapping from backend claims (e.g., `_lecturer`, `_tutor`) to frontend permissions to keep sidebar filtering consistent and ensure views disappear when access is revoked.
6. **Mock/test updates**
   - Expand `AuthService` mocks to include tutor personas and course assignments.
   - Add unit coverage for the role-to-navigation resolver and the new access bootstrap hook.

## Next Steps
- Validate UX expectations per role with stakeholders before implementing UI changes.
- Implement the authentication bootstrap and navigation refactor, then wire lecturer/tutor/student paged views to the existing backend endpoints.
- Ensure regression coverage by extending existing tests to cover the new role-aware flows.
