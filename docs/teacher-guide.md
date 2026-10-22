# Teacher guide: course dashboard

This guide is for lecturers and tutors who use the Computor web app to follow
their students' work. It explains what each page shows, where the numbers come
from, and what they do not tell you. No technical knowledge is needed.

Everything on these pages is computed from what the platform already records
when students work on assignments:

- **Test runs**: each time a student runs the automatic tests, the time, the
  score (0–100 %) and the test report are stored.
- **Submissions**: when a student officially submits an assignment, the time
  is stored.
- **Grades and feedback**: when a tutor or lecturer grades a submission, the
  grade, status, written feedback, grader and time are stored.

The platform does not record keystrokes, screen time or time spent in the
editor. Anything that looks like "time spent" is an estimate and is labelled
as one.

## Where to find the pages

Open a course and use the sidebar:

| Sidebar entry | Who sees it | What it is for |
|---|---|---|
| Lecturer → Grading | Lecturers and above | Course statistics, the student list with flags, and each student's detail page |
| Lecturer → Typical errors | Lecturers and above | The test failures that many students share |
| Tutor | Tutors and above | How much work is waiting for review |
| Tutor → Submissions | Tutors and above | The review queue |
| Tutor → Grading | Tutors and above | Grading one student at a time |

Tutors see only the Tutor pages. The Lecturer pages show data about the whole
course and are reserved for lecturers, course maintainers, course owners and
administrators.

## Course statistics (Lecturer → Grading)

The top of the page summarises the course:

- **Students**, **Average progress** and **Completed**: progress is the share
  of submittable assignments a student has officially submitted.
- **At risk**: students below 25 % progress.
- **Inactive**: students without a submission in the last 14 days.
- **Progress distribution** and the content-type chart show how the course is
  spread across progress levels and assignment types.

### Flags

Below the charts, the **Flags** panel lists simple, fixed rules that point out
students you may want to look at. A flag is a prompt to look, not a verdict:
each one says which rule fired and the numbers that triggered it. Open
**How flags are computed** on the page to see every rule with its threshold.

| Flag | When it appears |
|---|---|
| Many failed attempts | 10 or more test runs on one assignment without reaching the full score. Shown as a warning while the full score is still missing, as information once it was reached. |
| Sudden jump to full score | A test run reached 100 % directly after a run at or below 30 % on the same assignment. Often a student simply found the bug; it is not evidence of copying on its own. |
| Inactive | No test run and no submission in the last 14 days, or none at all. |
| Low progress | Fewer than 25 % of the submittable assignments submitted. |
| Last-minute submission | The last submission came less than 2 hours before the due date. |
| Submission after the due date | At least one submission after the due date. |

The platform does not store deadlines per assignment. The two deadline rules
use the **Due date** you enter in the Flags panel (or on a student's page). It
is remembered in your browser for this course and applies to all assignments,
so set it to the deadline you are interested in. Without a due date the two
deadline rules are skipped.

The student table has a **Flags** column. Hover over a flag to read its
reason, and tick **Only flagged** to list just the flagged students. Click a
student to open their detail page.

## A single student (Lecturer → Grading → a student)

The detail page shows, from top to bottom:

1. **Average grade, progress and submission counts.**
2. **Submission timeline**: the student's submissions accumulated over time,
   with the start and due date you set at the top of the page.
3. **Flags**: the same rules as above, for this student, each with its reason.
4. **Attempt timeline** (in German: *Bearbeitungsverlauf*): one row per
   assignment the student has worked on.
   - *Attempts over time*: dots are test runs, coloured by score (green: full
     score, amber: at least 50 %, red: below 50 %); bars are submissions; a
     dashed line marks the due date. All rows share one time axis, so you can
     see which assignment was worked on when.
   - *Runs* and *Submissions*: how many of each.
   - *First / last activity*: the first and last test run or submission.
   - *Full score reached*: when a test run first reached 100 %, or "not yet".
   - *Best / latest*: the best and the most recent test score.
   - *Days*: on how many different days the student worked on it.
   - *Median gap*: the typical time between two consecutive test runs.
   - *Est. active time*: an **estimate**. It adds up the gaps between
     consecutive test runs that are at most 30 minutes apart. Work done without
     running the tests is invisible to the platform, so read this as a lower
     bound, never as measured working time.
   - *Last submission* (only with a due date): how long before or after the
     due date the last submission came.
5. **History of runs, submissions and feedback**: everything in time order,
   newest first. A *Submission run* is a test run on an official submission;
   a *Grading* row shows the grade, its status, the written feedback and who
   gave it. Use the two filters to show one assignment or one kind of entry.
6. **Content tree**: every assignment with its status and number of attempts.

Use **Print** to get a paper or PDF copy of the page, for example for a
consultation with the student.

## Typical errors (Lecturer → Typical errors)

This page collects the failing tests from the students' test runs and groups
those that fail for the same reason. It helps you spot problems that many
students share, for example a misunderstood task or a missing hint.

For each group you see the assignment, the failing test, the error message,
how many **students** are affected and how many failing **runs** there were.
Groups affecting the most students come first. Click a row to see up to three
examples from different students with the original message and a link to that
student's page.

How messages are grouped: only the first line that names the error is kept,
and details that differ from student to student are replaced by placeholders:
numbers by `<n>`, quoted values by `<str>`, file paths by `<path>` and memory
addresses by `<addr>`. Plain names in quotes, such as `'np'` in
"name 'np' is not defined", are kept because they usually name the actual
problem. So "assert 3 == 4" and "assert 7 == 2" become one group,
"assert <n> == <n>".

Things to know:

- Only test runs by students count; lecturers' and tutors' own test runs are
  left out.
- The page reads the newest failing test runs, 300 by default. If more exist,
  a notice says so; choose a larger number or a single assignment to look
  further back.
- *Runs without report* counts runs for which no detailed test report was
  stored. They cannot contribute to any group.

## Tutor pages

### Tutor (overview)

Shows how many students you have, how many have ungraded submissions, the
number of ungraded submissions and unread messages, with links to the two
pages below.

### Submissions

The review queue: every student or team with submissions, by default only
those with ungraded work, oldest waiting first. Filter by assignment, or untick
**Only ungraded** to see everything. Click a row to open that student's
grading page at the right assignment.

### Grading

Choose a student from the list (tick **Only with ungraded submissions** to
narrow it down). The student page lists their assignments on the left; pick
one to see:

- the latest test result and the number of submissions and test runs,
- a form to **grade the latest submission**: a grade in percent, a status
  (*Corrected*, *Correction necessary*, *Improvement possible* or *Not
  reviewed*) and written feedback for the student,
- the earlier grades and feedback for this assignment,
- the details of the latest test run.

The grade field is pre-filled with the latest automatic test score; change it
as needed. When a grade refers to an older submission than the latest one,
the page says so.

## What the dashboard does not do

- It does not judge students automatically. Flags are fixed, visible rules
  with stated thresholds; there is no hidden score.
- It does not measure time spent working. The only time figure is the labelled
  estimate in the attempt timeline.
- It does not know assignment deadlines unless you enter a due date.
