"use client";

import dynamic from "next/dynamic";

const VisualV2Page = dynamic(
  () => import("./visual-v2-page").then((module) => module.VisualV2Page),
  { ssr: false },
);

export function VisualV2ClientEntry() {
  return <VisualV2Page />;
}
