import type { Metadata } from "next";
import { DataQualityPage } from "@/features/quality/data-quality-page";
export const metadata: Metadata = { title: "数据质量" };
export default function DataQualityLabPage() { return <DataQualityPage />; }
