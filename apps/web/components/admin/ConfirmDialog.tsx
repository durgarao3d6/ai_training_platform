"use client";

import { Button, Dialog, FormActions } from "@/components/ui/primitives";

import { ErrorList } from "./ErrorList";
import styles from "./admin.module.css";

/** Confirmation for destructive actions. Says what will happen and offers a safe way out. */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  busy,
  errors,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  busy: boolean;
  errors: string[];
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Dialog open={open} title={title} onClose={onClose}>
      <div className={styles.form}>
        <ErrorList errors={errors} />
        <p className={styles.confirmText}>{description}</p>
        <FormActions>
          <Button variant="secondary" onClick={onClose}>
            Keep it
          </Button>
          <Button variant="danger" icon="trash" busy={busy} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </FormActions>
      </div>
    </Dialog>
  );
}
