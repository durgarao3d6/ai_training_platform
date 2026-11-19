# AITMS – UI Design Brief and Reference Board

Version 0.3 prototype · Draft for design and frontend handover · 8 November 2026

### v0.3 change log

Product owner decisions of 8 November 2026. Implemented in code, not yet verified in a browser or with users.

- Visual direction changed from "Chalk and ink" to **Soft depth**: lavender-grey canvas, floating white cards with large radii and soft shadows, a floating sidebar with a solid ink active pill, solid ink primary buttons, violet for links and focus, and a pastel colour per track. Tokens are v0.3 in `docs/aitms-tokens.css` (sections 4, 5, 12.3, 12.5).
- Fonts changed: Plus Jakarta Sans for the interface (was Source Sans 3). Source Serif 4 and IBM Plex Mono are unchanged.
- Intern home now shows a hero for the course that most needs attention plus every enrolled course with a status (section 6.1). The intern "Course map" is now "My courses", with a map page per course.
- There is no sample data. The sample ribbon and SAMPLE tag are removed (sections 6.8 and 7). The only seeded data are the bootstrap accounts and role profiles.
- Admin course editor added: admins author courses, milestones, tasks, deliverable manifests and rubrics in the app (section 7). HR and admins also manage cohorts, enrollments and accounts.
- Accessibility requirements and microcopy rules are unchanged.

Companion documents: PRD (section 8 evaluation view, section 10 UX requirements) · Architecture Specification (section 15 frontend) · Implementation Plan. This brief is the detailed version of PRD section 10.

## 1. Purpose and status

This brief tells the designer and the frontend engineer what each screen should feel like and contain, and where the visual references came from.

**Status of the references:** they were collected from Dribbble search results and Mobbin's public pages. The research read titles and descriptions only, not the images, and Mobbin's screens are behind a login. Treat every reference as a starting point and **look at it before relying on it**. No reference is a template to copy.

## 2. Who we are designing for

These are hypotheses to test in the usability sessions (PRD section 10).

| Person | Emotional moment that matters most | Design consequence |
| --- | --- | --- |
| Intern | Reading feedback after a weak submission | Start with what is working, then three priorities, then a clear next step. Never open with a score |
| Trainer | Deciding whether to trust the AI | Evidence beside the submission, visible source of every finding, easy override |
| HR / management | Wanting an honest signal without a witch hunt | Show who needs support and why. Separate measured results from AI judgments |

## 3. Design principles

1. **Needing another pass is a step, not a verdict.** Use Needs another pass, never Failed or Rejected.
2. **Show where each judgment came from.** Label findings as Measured by tests, Read by AI, or Reviewed by a named trainer.
3. **Make the human visible.** Show the trainer's name. Offer Ask my trainer and I disagree.
4. **One main action per screen.** The intern should never have to decide what to do next.
5. **Compare people with their own past, not each other.** No leaderboards, streak pressure or cohort comparisons on intern screens.
6. **Be honest about uncertainty.** No fake precision such as 87% confidence. Say what a trainer will double-check and why.
7. **Practise what the UX track teaches.** Keyboard operation, real contrast, meaning never carried by colour alone.

## 4. Visual direction

Decided values (v0.3, "Soft depth"). They live in aitms-tokens.css, and every colour pair is computed against WCAG contrast thresholds in the token comments (section 12.3).

| Element | Direction |
| --- | --- |
| Background | Soft lavender-grey canvas (#F6F5FB). Cards float on it as white surfaces |
| Action and accent | Primary buttons and the active navigation pill are solid ink (#1B1A2E). Violet (#4B3FB5) is for links, focus and selected states only |
| Tracks | A pastel colour per track: developer peach, BA mint, QA lavender, UI/UX butter. Hero cards carry decorative circles in the track tones. Colour never replaces the track name |
| Status colours | Muted, always paired with text and an icon shape. Amber for Needs another pass; red only for system errors |
| Headings and interface | Plus Jakarta Sans. Bold for headings, sentence case |
| Feedback, briefs and trainer notes | Source Serif 4 at 17px with 1.6 line height. The serif is the human voice (human words) |
| Code and quoted evidence | IBM Plex Mono |
| Shape | Large radii (12px controls, 24px cards, 30px hero card), soft shadows that make cards float, thin decorative borders only |
| Density | Airy on the intern side; compact and table-first on trainer and HR side |

**Avoid:** purple-to-blue gradients, glass cards, 3D blob illustrations (the flat decorative circles on track hero cards are the one exception), emoji headings, stock illustration, rainbow charts, radar charts, rows of identical cards each with an icon and three words, and greetings like Hello, User.

**Use instead:** real content as the visuals (thumbnails of the intern's own submissions, the trainer's name), specific copy (Day 9 of 30. You are on chunking.), and unequal card sizes that reflect importance.

## 5. Layout systems

- **Intern: bento by importance.** The largest card is where you are now. Smaller cards support it. Cards are deliberately uneven, so the current task visibly outranks everything else. Cards are floating white surfaces with large radii and soft shadows.
- **Trainer and HR: table-first.** Dense tables with sticky headers, sortable columns, keyboard navigation and a side pane for detail. Charts are secondary and only where they answer a question.
- **Shell:** a floating white sidebar on desktop (248px), role-specific. The active item is a solid ink pill with white text. The content area is capped at 1360px. There is no sample data, so no ribbon appears.

## 6. Screen specifications

### 6.1 Intern home

An intern can be enrolled in several courses at once. Home shows all of them.

- Hero card: the course that most needs attention, in its track colour with decorative circles. It shows the current task with title, one-line why, time estimate, and a single primary button, Continue.
- My courses: a CourseCard for every enrolled course, each with a status in words and an icon: In progress, Not started, Waiting for review, Complete. Each card opens that course's map page.
- Latest feedback card: first line of the most recent feedback and its status.
- Milestone trail (not a grid) on each course map page: complete, current, locked. Locked steps say what unlocks them.
- Skills panel: horizontal bars with a marker for where you were at the first assessment.
- Trainer card: name, and the Ask my trainer action.

### 6.2 Task page

- Brief, learning objective and expected deliverables in plain language.
- How we will look at your work: the rubric criteria with a short description of good and not yet for each.
- Submission area for files, links and text, with accepted types stated.
- Ask my trainer.

### 6.3 While it is being evaluated

Show stages in human terms: Checking your files, Running your tests, Reading your explanation, Putting feedback together. Tell the intern they can close the tab and that the result will be waiting. Show a calm failure message if something breaks: Your work is saved and your trainer has been told.

### 6.4 Evaluation result (one shared component)

Order from top to bottom:

1. Status in plain words and a one-line summary.
2. What is working, with real evidence.
3. Work on these next: the top three; the rest collapsed.
4. Criterion bars that carry words as well as numbers, for example Level 3 of 4: handles overlap, misses empty input.
5. Each bar expands to the quoted evidence, highlighted in the intern's own submission.
6. Source label on every finding.
7. Review badge: Trainer review pending, with the reason on hover and an expected time.
8. Actions: Start correction, I disagree (P1), Ask a question.

### 6.5 Correction task panel

One correction at a time. Guiding questions, what to change, what to resubmit. Never the answer. A clear note that the previous attempt stays in history.

### 6.6 Trainer queue and review

- Table columns: intern, task, tool-measured result, AI result, why flagged, waiting time. Default sort by risk then waiting time.
- Review pane: AI evidence on the left, submission on the right, keyboard shortcuts for approve, request revision, override.
- Context card: attempt number and earlier weak criteria, so a trainer never reviews cold.
- Override needs a reason (presets plus free text). Optional personal note shown to the intern under the trainer's name.
- Agreement rate between trainers and the AI shown on a small panel (P1).

### 6.7 HR and management

- Overview table: intern, track, progress, status, and the reason for the status. Use Needs support, not red alarms.
- Skills needing attention across the cohort.
- Project readiness with its inputs listed, plus the BA to QA coverage matrix.
- Measured results and AI judgments shown separately.
- A visible note for what interns can see about themselves.

### 6.8 No sample data

There is no sample data (product decision, 8 November 2026). There is no ribbon, no SAMPLE tag and no pre-filled history. A fresh platform holds only the seeded accounts, so every list and card needs a designed empty state with a next step (section 6.9). Examples: "No courses yet. Create the first course" for an admin, and "You are not enrolled in a course yet. Your HR contact can enroll you" for an intern. FR-SMP-01 to FR-SMP-04 are withdrawn.

### 6.9 Empty, error and locked states

Every list and card has a designed empty state with a next step. Locked content explains what unlocks it. Errors say what happened, that work is safe, and who has been told.

## 7. Component inventory

| Component | Used on | Notes |
| --- | --- | --- |
| EvaluationResult | Intern, trainer | One component for all roles, driven by the result schema |
| CriterionBar | Evaluation | Words plus level, expandable evidence |
| EvidenceQuote | Evaluation, review | Monospace, highlighted in context, verified flag |
| SourceLabel | Findings | Measured by tests, Read by AI, Reviewed by a trainer |
| ReviewBadge | Evaluation, queue | Reason and expected time |
| MilestoneTrail | Course map page | Complete, current, locked with unlock reason |
| StageProgress | While evaluating | Human-language stages, SSE-driven |
| BentoCard | Intern home | Sizes by importance; floating white surface, large radius |
| CourseCard | Intern home, My courses | Track colour beside the track name, course title, progress in words, status (In progress, Not started, Waiting for review, Complete) with icon |
| StatTile | Trainer, HR, admin overviews | One number with a plain label and its source; no ranking |
| CourseEditor (admin) | Admin | Course, milestone and task tree; deliverable manifest; rubric editor with draft, publish and frozen versions; shows who published and when |
| DataTable | Trainer, HR | Sticky header, sort, filter, keyboard |
| ContextCard | Trainer review | Attempt history, weak criteria |
| CoverageMatrix | HR, BA to QA | Requirements against tests, from the graph query |

## 8. Microcopy guide

| Instead of | Say |
| --- | --- |
| Submission failed | Needs another pass |
| Low confidence | A trainer will take a second look |
| Error 500 | We could not finish checking your work. It is saved and your trainer has been told. |
| Great job! | Your overlap handling is solid. Next, look at empty input. |
| Rejected | Not yet. Here is what to work on |
| Score: 62 | Level 2 of 4 on edge cases. Two things to try next |

Tone: calm, specific, respectful, plain words. No exclamation marks in feedback.

## 9. Reference board

| For this screen | Reference | What to borrow | Link |
| --- | --- | --- | --- |
| Intern home | Personal e-learning dashboard (Plume, Dribbble) | Learner lands straight on their enrolled courses; no searching or clicking around | https://dribbble.com/shots/11999865-Personal-e-learning-dashboard-lms-learning-management-system |
| Intern home | LMS student dashboard (Lixco, Dribbble) | A single portal that brings resources and communication together | https://dribbble.com/shots/25259925-Learning-management-system-student-dashboard |
| Intern home layout | EduSync bento-style LMS (Dribbble tag page) | Bento grid composition to adapt with uneven card sizes | https://dribbble.com/ryanindraaaa/tags/learning-management-system |
| Trainer view | LMS Dashboard (Dribbble) | High-level view of learners plus the ability to reach out to those who are struggling | https://www.dribbble.com/shots/4687133-LMS-Dashboard |
| Trainer view | EasySpeak tutor dashboard (Dribbble) | Tutor homepage showing student progress and dynamics | https://dribbble.com/shots/20684982-Learning-Dashboard |
| HR overview | Employee Onboarding Analytics Dashboard (Adeptly, Dribbble) | Training analytics for HR at a glance | https://dribbble.com/shots/24205804-Employee-Onboarding-Analytics-Dashboard-LMS |
| HR overview | LMS Analytics screen (Adeptly, Dribbble) | Behavioural analytics layout | https://dribbble.com/shots/24205837-Learning-Management-System-LMS-Analytics |
| HR tables and themes | Tracky HR dashboard (Dribbble) | Light and dark versions of a dense dashboard | https://dribbble.com/shots/22597543-Tracky-HR-Management-Dashboard |
| HR tables | HR Dashboard collection (Dribbble) | Table, modal and detail patterns | https://dribbble.com/ifeomacreates/collections/7725421-HR-Dashboard |

### Mobbin

Mobbin is a large library of real app and web screens and flows (https://mobbin.com/). Full flow access is paid. Suggested searches: Dashboard, Progress, Empty state, Table, Filter, Settings (web); flows for Onboarding and Review or Approval; any milestone path or skill tree reference. Alternatives for web-app patterns: Refero and SaaSUI (https://www.saasui.design/best-saas-ui-design-inspiration).

### Not found on Dribbble

Nothing in the search covered the evaluation result screen (criterion scores, quoted evidence, findings, correction). Suggested sources from the team's own product knowledge, not verified in this research: pull request review screens on GitHub or GitLab (findings beside evidence, status checks), issue detail pages in Linear or Jira (correction task panel), and lesson feedback in Duolingo or Brilliant (success and retry states). Collect screenshots of these into the design file and annotate what is borrowed.

## 10. Accessibility requirements

- WCAG 2.2 AA contrast for all text and controls; verified with a tool, not by eye.
- Full keyboard operation for every action, including the evidence expanders and the review pane shortcuts.
- Visible focus states; target sizes of at least 24 by 24 CSS pixels (aim for 44 on touch).
- Meaning never carried by colour alone: status has text and an icon; track colours always sit beside the track name.
- Respect reduced-motion preferences. Live progress updates announced politely to screen readers.
- Automated accessibility checks in CI plus a manual keyboard pass per phase.

## 11. Usability validation plan

Run 6–8 short sessions before the pilot: interns from different tracks, two trainers and one HR user.

| Participant | Task | Success looks like |
| --- | --- | --- |
| Intern | Read a weak result and say what to do next | Correct next action within 30 seconds, without distress cues |
| Trainer | Find the riskiest item in the queue and decide | Finds it in under a minute and can explain why it was flagged |
| HR | Find who needs support and why | Names the right intern and the reason |

Open questions to settle by observation: does leading with a summary instead of a score feel caring or evasive; does Needs another pass feel honest; do worded bars beat a radar chart; do interns understand the review badge.

## 12. Handoff and design decisions

All five open items are decided below. Two of them need a person to confirm: the table density default (with the two trainers) and the readiness definition (with the product owner). Those are proposals made without them in the room.

### 12.1 Figma file structure

One file, pages in this order. Page numbers show reading order.

| Page | Contents | Rule |
| --- | --- | --- |
| 00 Read me | Purpose, status legend, link to the tokens file, version log, owner | Updated at every handoff |
| 01 Foundations | Variables for colour, type, spacing, radius, motion; type specimens; contrast table | Variable names match aitms-tokens.css exactly |
| 02 Components | Every component in section 7 with variants and a usage note | Auto layout throughout; no detached instances |
| 03 Intern flows | Home, my courses, course map, task, evaluating, result, correction | One section per flow, frames left to right in task order |
| 04 Trainer flows | Queue, review pane, override, intern context card | Keyboard shortcuts annotated on the frames |
| 05 HR flows | Overview, skills, readiness, coverage matrix | Readiness card follows section 12.6 |
| 06 States | Empty, error, locked, loading, long text, no permission | A grid: screens down, states across |
| 07 Handoff | Frames marked Ready for dev, with annotations | Only frames on this page are built |
| 99 Archive | Old explorations | Never deleted |

Conventions: name frames as flow / screen / state (for example Intern / Result / Needs another pass). Mark each section Exploring, In review or Ready for dev. Use realistic content written for the design, never lorem ipsum, and never invented scores shown as real results. Resolve all comments before a frame moves to Handoff. Variable collections have one mode (Light) plus an empty Dark mode reserved for later.

### 12.2 Tokens as a single file

`aitms-tokens.css` is the one file the frontend imports. It holds semantic tokens only, and components never contain raw colour values. Figma Variables use the same names (--color-accent is color/accent). For the prototype the designer and frontend engineer sync them by hand at each handoff, and a CI script fails the build if any colour pair drops below its contrast target. Automating the export from Figma is a pilot task.

### 12.3 Accent colour, fonts and contrast

**Action: solid ink, #1B1A2E. Accent: violet, #4B3FB5.** Primary buttons and the active navigation pill are solid ink, so the one main action on a screen is the darkest thing on it (white on ink is 17.02). Violet is used only for links, focus and selected states, and it stays clear of the status colours (green, amber, slate, red) so it never competes with meaning. Each track has a pastel surface, two decorative circle tones and a readable ink: developer peach, BA mint, QA lavender, UI/UX butter. The second signature is the evidence highlighter (#FFE680), used only on text quoted from the intern's own submission.

**Fonts: Plus Jakarta Sans, Source Serif 4 and IBM Plex Mono, chosen by voice.** Sans is the interface and headings (bold, sentence case). Serif is human words: written feedback, task briefs and trainer notes, set at 17px with 1.6 line height and lines under 68 characters. Mono is verbatim text from a submission, and code. Plus Jakarta Sans is rounded and friendly, Source Serif 4 is clearly a different voice, and Plex Mono is distinct (0 and O, 1 and l). All three are open licence and self-hosted through @fontsource packages, so the demo needs no font CDN. Tables and scores use tabular figures.

**What changed in v0.3.** The v0.2 direction (neutral chalk canvas, ink blue accent, Source Sans 3, thin borders) is replaced by Soft depth: a lavender-grey canvas (#F6F5FB), floating cards, solid ink actions and track pastels. The serif still carries meaning (a human is speaking) instead of decoration.

**Type scale:** 12, 14, 16, 17, 18, 22, 34 and 40 px (34 for page titles, 40 for the hero task title). Nothing below 12px; body 16px; table cells 14px.

Contrast, computed with the WCAG 2.x formula and recorded in the comments of aitms-tokens.css (main pairs below):

| Pair | Ratio | Needed |
| --- | --- | --- |
| Primary text on canvas | 15.70 | 4.5 |
| Secondary text on canvas | 6.49 | 4.5 |
| Tertiary text on the sunken surface | 4.89 | 4.5 |
| White on solid ink (primary button, active pill) | 17.02 | 4.5 |
| Violet accent on white; white on violet | 7.84 | 4.5 |
| Control border on white / on canvas | 3.37 / 3.11 | 3.0 |
| Focus ring (violet) on canvas | 7.24 | 3.0 |
| Track ink on its pastel: developer / BA / QA / UI/UX | 7.64 / 6.88 / 8.10 / 7.06 | 4.5 |
| Needs another pass text on its tint | 6.35 | 4.5 |
| Approved text on its tint | 5.54 | 4.5 |
| Trainer review pending text on its tint | 7.76 | 4.5 |
| System error text on its tint | 6.17 | 4.5 |
| Locked text on its tint | 5.16 | 4.5 |
| Text on the evidence highlight | 13.17 (v0.2 value, not restated in the v0.3 token comments) | 4.5 |

This is a computed check. It does not replace testing real screens with a browser tool and a keyboard pass.

### 12.4 Table density for trainers

**Decision: three modes, and the middle one is the default.** Default is a 40px row with 14px text. Compact is 32px for trainers who want more rows. Comfortable is 48px with 16px text, for reviewing with someone else. At Default, a full-height window on a 1080p screen fits roughly 19 rows (my estimate), enough to scan a day's queue without much scrolling. Every mode keeps targets of 24px or more. The choice is remembered per table and per person. Rows have 1px separators, no zebra stripes, a sticky header, and risk shown as text plus an icon.

**To confirm with the two trainers:** give each a three-minute task, find the riskiest item and decide, once at Default and once at Compact. Compare time and mistakes, and ask which they would keep. Change the default only if both prefer another mode. I have not tested this with them.

### 12.5 Dark mode

**Decision: not in the prototype or the pilot unless users ask for it.** It would double the contrast checks, and the evidence highlight, status tints, track pastels and soft shadows would all need redesign, with no user need identified yet. The system is ready for it: semantic tokens only, no raw colours in components, a reserved Dark mode in Figma and a data-theme hook. Revisit if two or more trainers or interns ask, or if HR wants to present on a projector.

### 12.6 How readiness is displayed

This is a proposal for the product owner to confirm (PRD open question 2). I cannot confirm it on their behalf.

**Principle: readiness is a conversation starter with evidence, never a score.** Show a three-state label, Not yet, Getting close or Ready for project work, and always show the checklist that produced it. No percentage ring, no ranking.

| Condition | Source | Met when |
| --- | --- | --- |
| Required milestones approved | Progression | Every milestone before the project stage is approved (the list is set by the product owner) |
| No overdue corrections | Corrections | No correction task open longer than N days (N set by the product owner) |
| No unresolved review flags | Review | The trainer queue has nothing waiting for this intern |
| Handoffs accepted | Traceability | The next role accepted this person's deliverable, for example QA accepted the BA requirements |
| Trainer sign-off | Review | A named trainer has written a short statement and dated it |

Proposed rule: Ready for project work when all five are met; Getting close when three or four are met; Not yet otherwise. The project gets the same treatment: required deliverables approved per role, the BA to QA coverage matrix with a threshold set by the product owner, the count of open blocking defects, and a final trainer sign-off.

Each row on screen has an icon, text, a link to its evidence, and a source tag (Measured, or Judged by a trainer). An unmet row says what would meet it. The trainer's sign-off statement is quoted with name and date. Interns see the same card about themselves as HR does (NFR-PRV-02).

**Needed from the product owner:** the milestone list, the value of N, the coverage threshold and who may sign off. A 20-minute review of the readiness card with the product owner settles these.
