"use client";

import { useState } from "react";

import { Button, Dialog, Field, FormActions, inputClass } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { CourseAdmin, ModuleAdmin, RubricAdmin, TaskAdmin } from "@/lib/types";

import styles from "./admin.module.css";
import { type DeliverableDraft, DeliverablesEditor, deliverablesPayload, draftsFromDeliverables } from "./DeliverablesEditor";
import { ErrorList } from "./ErrorList";
import { useAction } from "./useAction";

function text(form: FormData, name: string): string {
  return String(form.get(name) ?? "").trim();
}

// ---------- Course ----------

export function CourseDialog({
  open,
  course,
  onClose,
  onSaved,
}: {
  open: boolean;
  course: CourseAdmin;
  onClose: () => void;
  onSaved: (course: CourseAdmin) => void;
}) {
  return (
    <Dialog open={open} title="Edit course" description="The track cannot change once a course exists." onClose={onClose}>
      <CourseForm course={course} onClose={onClose} onSaved={onSaved} />
    </Dialog>
  );
}

function CourseForm({
  course,
  onClose,
  onSaved,
}: {
  course: CourseAdmin;
  onClose: () => void;
  onSaved: (course: CourseAdmin) => void;
}) {
  const action = useAction();

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const saved = await action.run(() =>
      api.patch<CourseAdmin>(`/admin/courses/${course.id}`, {
        title: text(form, "title"),
        description: text(form, "description"),
        final_deliverable: text(form, "final_deliverable"),
      }),
    );
    if (saved) {
      onSaved(saved);
      onClose();
    }
  }

  return (
    <form onSubmit={submit} className={styles.form}>
      <ErrorList errors={action.errors} />
      <Field label="Title">
        {(p) => <input {...p} name="title" className={inputClass} defaultValue={course.title} required maxLength={200} />}
      </Field>
      <Field label="Description">
        {(p) => (
          <textarea {...p} name="description" className={inputClass} rows={3} maxLength={5000} defaultValue={course.description} />
        )}
      </Field>
      <Field label="Final deliverable" hint="What an intern has produced by the end of the course.">
        {(p) => (
          <input {...p} name="final_deliverable" className={inputClass} maxLength={2000} defaultValue={course.final_deliverable} />
        )}
      </Field>
      <FormActions>
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" busy={action.busy}>
          Save course
        </Button>
      </FormActions>
    </form>
  );
}

// ---------- Milestone ----------

export function ModuleDialog({
  open,
  courseId,
  milestone,
  onClose,
  onSaved,
}: {
  open: boolean;
  courseId: string;
  /** Pass a milestone to edit it; leave out to add a new one. */
  milestone?: ModuleAdmin | null;
  onClose: () => void;
  onSaved: (course: CourseAdmin) => void;
}) {
  return (
    <Dialog
      open={open}
      title={milestone ? "Edit milestone" : "Add milestone"}
      description="A milestone groups tasks. Interns unlock the next one when they finish this one."
      onClose={onClose}
    >
      <ModuleForm courseId={courseId} milestone={milestone ?? null} onClose={onClose} onSaved={onSaved} />
    </Dialog>
  );
}

function ModuleForm({
  courseId,
  milestone,
  onClose,
  onSaved,
}: {
  courseId: string;
  milestone: ModuleAdmin | null;
  onClose: () => void;
  onSaved: (course: CourseAdmin) => void;
}) {
  const action = useAction();

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = {
      title: text(form, "title"),
      description: text(form, "description"),
      learning_objective: text(form, "learning_objective"),
    };
    const saved = await action.run(() =>
      milestone
        ? api.patch<CourseAdmin>(`/admin/modules/${milestone.id}`, body)
        : api.post<CourseAdmin>(`/admin/courses/${courseId}/modules`, body),
    );
    if (saved) {
      onSaved(saved);
      onClose();
    }
  }

  return (
    <form onSubmit={submit} className={styles.form}>
      <ErrorList errors={action.errors} />
      <Field label="Title">
        {(p) => <input {...p} name="title" className={inputClass} defaultValue={milestone?.title ?? ""} required maxLength={200} />}
      </Field>
      <Field label="Description">
        {(p) => (
          <textarea {...p} name="description" className={inputClass} rows={3} maxLength={5000} defaultValue={milestone?.description ?? ""} />
        )}
      </Field>
      <Field label="Learning objective" hint="What an intern can do after this milestone.">
        {(p) => (
          <textarea
            {...p}
            name="learning_objective"
            className={inputClass}
            rows={2}
            maxLength={2000}
            defaultValue={milestone?.learning_objective ?? ""}
          />
        )}
      </Field>
      <FormActions>
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" busy={action.busy}>
          {milestone ? "Save milestone" : "Add milestone"}
        </Button>
      </FormActions>
    </form>
  );
}

// ---------- Task ----------

export function TaskDialog({
  open,
  moduleId,
  task,
  onClose,
  onSaved,
}: {
  open: boolean;
  /** The milestone a new task is added to (ignored when editing). */
  moduleId: string;
  /** Pass a task to edit it; leave out to add a new one. */
  task?: TaskAdmin | null;
  onClose: () => void;
  onSaved: (course: CourseAdmin) => void;
}) {
  return (
    <Dialog
      open={open}
      title={task ? "Edit task" : "Add task"}
      description="Tell the intern what to do and what to hand in."
      onClose={onClose}
      wide
    >
      <TaskForm moduleId={moduleId} task={task ?? null} onClose={onClose} onSaved={onSaved} />
    </Dialog>
  );
}

function TaskForm({
  moduleId,
  task,
  onClose,
  onSaved,
}: {
  moduleId: string;
  task: TaskAdmin | null;
  onClose: () => void;
  onSaved: (course: CourseAdmin) => void;
}) {
  const action = useAction();
  const [deliverables, setDeliverables] = useState<DeliverableDraft[]>(() =>
    task ? draftsFromDeliverables(task.deliverables) : [],
  );

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = {
      title: text(form, "title"),
      task_type: text(form, "task_type"),
      depth: text(form, "depth"),
      description: text(form, "description"),
      learning_objective: text(form, "learning_objective"),
      submits: text(form, "submits"),
      evaluated_on: text(form, "evaluated_on"),
      requires_review: form.get("requires_review") === "on",
      // An empty list means "use the generic one-item manifest" (the API default), on create and edit.
      deliverables: deliverablesPayload(deliverables),
    };
    const saved = await action.run(() =>
      task ? api.patch<CourseAdmin>(`/admin/tasks/${task.id}`, body) : api.post<CourseAdmin>(`/admin/modules/${moduleId}/tasks`, body),
    );
    if (saved) {
      onSaved(saved);
      onClose();
    }
  }

  return (
    <form onSubmit={submit} className={styles.form}>
      <ErrorList errors={action.errors} />
      <Field label="Title">
        {(p) => <input {...p} name="title" className={inputClass} defaultValue={task?.title ?? ""} required maxLength={200} />}
      </Field>
      <div className={styles.grid2}>
        <Field label="Type">
          {(p) => (
            <select {...p} name="task_type" className={inputClass} defaultValue={task?.task_type ?? "practical"}>
              <option value="practical">Practical</option>
              <option value="integration">Integration</option>
              <option value="assessment">Assessment</option>
            </select>
          )}
        </Field>
        <Field label="Depth" hint="Demo tasks are fully built with automatic checks; content tasks are reviewed manually.">

          {(p) => (
            <select {...p} name="depth" className={inputClass} defaultValue={task?.depth ?? "content"}>
              <option value="content">Content</option>
              <option value="demo">Demo</option>
            </select>
          )}
        </Field>
      </div>
      <Field label="Task description" hint="Shown to the intern as the brief.">
        {(p) => (
          <textarea
            {...p}
            name="description"
            className={inputClass}
            rows={5}
            required
            maxLength={10000}
            defaultValue={task?.description ?? ""}
          />
        )}
      </Field>
      <Field label="Learning objective">
        {(p) => (
          <input {...p} name="learning_objective" className={inputClass} maxLength={2000} defaultValue={task?.learning_objective ?? ""} />
        )}
      </Field>
      <div className={styles.grid2}>
        <Field label="What the intern submits">
          {(p) => <input {...p} name="submits" className={inputClass} maxLength={2000} defaultValue={task?.submits ?? ""} />}
        </Field>
        <Field label="What it is evaluated on">
          {(p) => <input {...p} name="evaluated_on" className={inputClass} maxLength={2000} defaultValue={task?.evaluated_on ?? ""} />}
        </Field>
      </div>
      <label className={styles.check}>
        <input type="checkbox" name="requires_review" defaultChecked={task?.requires_review ?? false} />A trainer reviews every result for this task
      </label>
      <DeliverablesEditor value={deliverables} onChange={setDeliverables} />
      <FormActions>
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" busy={action.busy}>
          {task ? "Save task" : "Add task"}
        </Button>
      </FormActions>
    </form>
  );
}

// ---------- Rubric ----------

const LEVELS = ["0", "1", "2", "3", "4"] as const;

interface CriterionDraft {
  key: number;
  id: string | null;
  title: string;
  weight: string;
  minLevel: string;
  levels: Record<string, string>;
  boundChecks: string[];
  correction: string;
}

function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 60);
}

function draftsFrom(rubric: RubricAdmin | null): CriterionDraft[] {
  if (!rubric) return [];
  const saved = rubric.content.criteria;
  if (saved && saved.length) {
    return saved.map((c, i) => ({
      key: i,
      id: c.id,
      title: c.title ?? "",
      weight: String(c.weight),
      minLevel: c.mandatory_min_level ? String(c.mandatory_min_level) : "",
      levels: { ...c.levels },
      boundChecks: c.bound_checks ?? [],
      correction: c.correction_template ?? "",
    }));
  }
  return rubric.criteria.map((c, i) => ({
    key: i,
    id: c.id,
    title: c.title,
    weight: String(c.weight),
    minLevel: c.mandatory_min_level ? String(c.mandatory_min_level) : "",
    levels: { ...c.levels },
    boundChecks: [],
    correction: "",
  }));
}

export function RubricDialog({
  open,
  task,
  checkers,
  onClose,
  onSaved,
}: {
  open: boolean;
  task: TaskAdmin;
  /** Automatic checks the course's track allows. */
  checkers: string[];
  onClose: () => void;
  onSaved: (course: CourseAdmin) => void;
}) {
  return (
    <Dialog
      open={open}
      title={`Marking guide: ${task.title}`}
      description="Save a draft any time. Publishing checks that the guide is complete, then interns are marked against it."
      onClose={onClose}
      wide
    >
      <RubricForm task={task} checkers={checkers} onClose={onClose} onSaved={onSaved} />
    </Dialog>
  );
}

function RubricForm({
  task,
  checkers,
  onClose,
  onSaved,
}: {
  task: TaskAdmin;
  checkers: string[];
  onClose: () => void;
  onSaved: (course: CourseAdmin) => void;
}) {
  const source = task.draft_rubric ?? task.published_rubric;
  const [threshold, setThreshold] = useState(String(source?.pass_threshold ?? 70));
  const [enabled, setEnabled] = useState<string[]>(source?.checkers ?? []);
  const [criteria, setCriteria] = useState<CriterionDraft[]>(() => draftsFrom(source));
  const [nextKey, setNextKey] = useState(() => (source ? source.criteria.length + 100 : 100));
  const action = useAction();

  const total = criteria.reduce((sum, c) => sum + (Number.parseInt(c.weight, 10) || 0), 0);

  function patchCriterion(key: number, change: Partial<CriterionDraft>) {
    setCriteria((list) => list.map((c) => (c.key === key ? { ...c, ...change } : c)));
  }

  function toggle(list: string[], value: string): string[] {
    return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
  }

  function toggleEnabled(checker: string) {
    const next = toggle(enabled, checker);
    setEnabled(next);
    setCriteria((list) => list.map((c) => ({ ...c, boundChecks: c.boundChecks.filter((b) => next.includes(b)) })));
  }

  function addCriterion() {
    setCriteria((list) => [
      ...list,
      { key: nextKey, id: null, title: "", weight: "10", minLevel: "", levels: {}, boundChecks: [], correction: "" },
    ]);
    setNextKey((k) => k + 1);
  }

  function buildBody() {
    const used = new Set<string>();
    const payload = criteria.map((c, i) => {
      let id = c.id ?? (slug(c.title) || `criterion_${i + 1}`);
      while (used.has(id)) id = `${id}_${i + 1}`;
      used.add(id);
      const levels: Record<string, string> = {};
      for (const level of LEVELS) levels[level] = (c.levels[level] ?? "").trim();
      return {
        id,
        title: c.title.trim(),
        weight: Number.parseInt(c.weight, 10) || 1,
        mandatory_min_level: c.minLevel ? Number.parseInt(c.minLevel, 10) : null,
        levels,
        bound_checks: c.boundChecks,
        correction_template: c.correction.trim(),
      };
    });
    return { pass_threshold: Number.parseFloat(threshold) || 0, criteria: payload, checkers: enabled };
  }

  async function save(publish: boolean) {
    const saved = await action.run(async () => {
      const draft = await api.put<CourseAdmin>(`/admin/tasks/${task.id}/rubric-draft`, buildBody());
      return publish ? api.post<CourseAdmin>(`/admin/tasks/${task.id}/rubric-draft/publish`) : draft;
    });
    if (saved) {
      onSaved(saved);
      onClose();
    }
  }

  return (
    <form
      className={styles.form}
      onSubmit={(event) => {
        event.preventDefault();
        void save(false);
      }}
    >
      <ErrorList errors={action.errors} />
      {task.published_rubric && (
        <p className={styles.hint}>
          Version {task.published_rubric.version} is live. Publishing this draft creates version {task.published_rubric.version + 1}.
        </p>
      )}
      <div className={styles.grid2}>
        <Field label="Pass threshold (%)" hint="The score an attempt needs to count as passed.">
          {(p) => (
            <input
              {...p}
              className={inputClass}
              type="number"
              min={0}
              max={100}
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
          )}
        </Field>
        {checkers.length > 0 && (
          <fieldset className={styles.checks}>
            <legend>Automatic checks for this task</legend>
            {checkers.map((c) => (
              <label key={c} className={styles.check}>
                <input type="checkbox" checked={enabled.includes(c)} onChange={() => toggleEnabled(c)} />
                {c}
              </label>
            ))}
          </fieldset>
        )}
      </div>

      <div className={styles.subhead}>
        <h3>Criteria</h3>
        <span className={`${styles.weightSum} ${total === 100 ? styles.weightOk : styles.weightOff}`}>
          Weights add up to {total} of 100
        </span>
      </div>

      {criteria.length === 0 && <p className={styles.hint}>No criteria yet. Add the first one below.</p>}

      {criteria.map((c, index) => (
        <div key={c.key} className={styles.itemBox}>
          <div className={styles.itemHead}>
            <strong>Criterion {index + 1}</strong>
            <Button size="sm" variant="ghost" icon="trash" onClick={() => setCriteria((list) => list.filter((x) => x.key !== c.key))}>
              Remove
            </Button>
          </div>
          <div className={styles.grid3}>
            <Field label="Title">
              {(p) => <input {...p} className={inputClass} value={c.title} maxLength={200} onChange={(e) => patchCriterion(c.key, { title: e.target.value })} />}
            </Field>
            <Field label="Weight (1 to 100)">
              {(p) => (
                <input
                  {...p}
                  className={inputClass}
                  type="number"
                  min={1}
                  max={100}
                  value={c.weight}
                  onChange={(e) => patchCriterion(c.key, { weight: e.target.value })}
                />
              )}
            </Field>
            <Field label="Must reach level" hint="Below it, the task cannot pass.">
              {(p) => (
                <select {...p} className={inputClass} value={c.minLevel} onChange={(e) => patchCriterion(c.key, { minLevel: e.target.value })}>
                  <option value="">Not required</option>
                  {["1", "2", "3", "4"].map((l) => (
                    <option key={l} value={l}>
                      Level {l}
                    </option>
                  ))}
                </select>
              )}
            </Field>
          </div>
          {LEVELS.map((level) => (
            <Field key={level} label={`Level ${level}`}>
              {(p) => (
                <input
                  {...p}
                  className={inputClass}
                  value={c.levels[level] ?? ""}
                  onChange={(e) => patchCriterion(c.key, { levels: { ...c.levels, [level]: e.target.value } })}
                />
              )}
            </Field>
          ))}
          {enabled.length > 0 && (
            <fieldset className={styles.checks}>
              <legend>Automatic checks that feed this criterion</legend>
              {enabled.map((checker) => (
                <label key={checker} className={styles.check}>
                  <input
                    type="checkbox"
                    checked={c.boundChecks.includes(checker)}
                    onChange={() => patchCriterion(c.key, { boundChecks: toggle(c.boundChecks, checker) })}
                  />
                  {checker}
                </label>
              ))}
            </fieldset>
          )}
          <Field label="Correction note" hint="Short sentence shown when an intern misses this criterion.">
            {(p) => (
              <input
                {...p}
                className={inputClass}
                maxLength={200}
                value={c.correction}
                onChange={(e) => patchCriterion(c.key, { correction: e.target.value })}
              />
            )}
          </Field>
        </div>
      ))}

      <div>
        <Button variant="secondary" icon="plus" onClick={addCriterion}>
          Add criterion
        </Button>
      </div>

      <FormActions>
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="secondary" busy={action.busy}>
          Save draft
        </Button>
        <Button busy={action.busy} onClick={() => void save(true)}>
          Save and publish
        </Button>
      </FormActions>
    </form>
  );
}
