import { Icon } from "@/components/ui/Icon";
import styles from "./authoring.module.css";

/** Marks anything an AI wrote. A person must review it before it goes anywhere (FR-FB-03 style). */
export function AiLabel({ text = "AI suggestion, needs review" }: { text?: string }) {
  return (
    <span className={styles.aiLabel}>
      <Icon name="target" size={14} />
      {text}
    </span>
  );
}
