import type { Metadata } from "next";
import { RoleIntelligence } from "@/features/roles/role-intelligence";
export const metadata: Metadata = { title: "岗位洞察" };
export default function RolesLabPage() { return <RoleIntelligence />; }
