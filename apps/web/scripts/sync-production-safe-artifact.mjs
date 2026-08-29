import { copyFile, mkdir, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(webRoot, "../..");
const artifactRoot = resolve(repositoryRoot, "data/production-safe/current");
const destinationRoot = resolve(webRoot, "public/backend-data");
const files = [
  "artifact_metadata.json",
  "artifact_inventory.json",
  "quality_snapshot.json",
  "relation_aggregates.json",
  "role_aggregates.json",
  "skill_aggregates.json",
];

const metadata = JSON.parse(await readFile(resolve(artifactRoot, "artifact_metadata.json"), "utf8"));
if (metadata.classification !== "PUBLIC_SAFE" || metadata.source_snapshot !== "freehire_china_tech_2026_08") {
  throw new Error("Refusing to package an artifact that has not passed the frozen production-safe gate");
}

await mkdir(destinationRoot, { recursive: true });
for (const file of files) await copyFile(resolve(artifactRoot, file), resolve(destinationRoot, file));
