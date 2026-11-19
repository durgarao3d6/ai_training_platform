import { RoleGuard } from "@/components/shell/RoleGuard";

export default function InternLayout({ children }: { children: React.ReactNode }) {
  return <RoleGuard shell="intern">{children}</RoleGuard>;
}
