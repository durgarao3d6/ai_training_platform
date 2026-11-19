"use client";

import { useState } from "react";

import { ErrorList } from "@/components/admin/ErrorList";
import { useAction } from "@/components/admin/useAction";
import { Button } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { CourseAdmin } from "@/lib/types";

import styles from "./authoring.module.css";
import { AttachDialog } from "./AttachDialog";
import { ComponentList } from "./ComponentList";
import { MaterialDialog } from "./MaterialDialog";

/** Authoring actions for one milestone. Shared by the trainer workspace and the admin editor. */
export function MilestoneTools({
  moduleId,
  title,
  status,
  isAdmin,
  aiEnabled,
  onCourseChanged,
}: {
  moduleId: string;
  title: string;
  status: "draft" | "approved";
  isAdmin: boolean;
  aiEnabled: boolean;
  onCourseChanged: (course: CourseAdmin | null) => void;
}) {
  const [attach, setAttach] = useState(false);
  const [material, setMaterial] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const approve = useAction();

  async function approveModule() {
    const saved = await approve.run(() => api.post<CourseAdmin>(`/authoring/modules/${moduleId}/approve`, {}));
    if (saved) onCourseChanged(saved);
  }

  return (
    <div>
      <ErrorList errors={approve.errors} />
      <div className={styles.toolbarRow}>
        <Button size="sm" variant="secondary" icon="plus" onClick={() => setAttach(true)}>
          Attach with assistant
        </Button>
        <Button size="sm" variant="secondary" icon="file" onClick={() => setMaterial(true)}>
          Material
        </Button>
        {isAdmin && status === "draft" && (
          <Button size="sm" icon="check" busy={approve.busy} onClick={() => void approveModule()}>
            Approve and publish milestone
          </Button>
        )}
      </div>
      <ComponentList moduleId={moduleId} isAdmin={isAdmin} refreshKey={refresh} />
      <AttachDialog
        open={attach}
        moduleId={moduleId}
        moduleTitle={title}
        aiEnabled={aiEnabled}
        onClose={() => setAttach(false)}
        onChanged={() => setRefresh((n) => n + 1)}
      />
      <MaterialDialog
        open={material}
        moduleId={moduleId}
        moduleTitle={title}
        aiEnabled={aiEnabled}
        onClose={() => setMaterial(false)}
        onChanged={() => setRefresh((n) => n + 1)}
      />
    </div>
  );
}
