import { RoleGuard } from "@/components/shell/RoleGuard";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <RoleGuard shell="admin">{children}</RoleGuard>;
}
