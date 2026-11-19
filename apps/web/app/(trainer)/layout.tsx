import { RoleGuard } from "@/components/shell/RoleGuard";

export default function TrainerLayout({ children }: { children: React.ReactNode }) {
  return <RoleGuard shell="trainer">{children}</RoleGuard>;
}
