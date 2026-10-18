import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "../..");
const readText = (path) => readFileSync(resolve(repoRoot, path), "utf8");
const readJson = (path) => JSON.parse(readText(path));

const compatibilityPath =
  "packages/release-model/src/al-isabah-governance.compatibility.json";
const projectionPath =
  "packages/release-model/src/al-isabah-honorifics.projection.json";

test("Sabiqah has no local Al-Isabah translation-execution authority", () => {
  for (const path of [
    "docs/contracts/translation-quality-workflow.md",
    "docs/translation-profiles/al-isabah.md",
    "packages/release-model/src/honorifics.registry.json",
  ]) {
    assert.equal(existsSync(resolve(repoRoot, path)), false, path);
  }

  const registry = readJson("docs/contracts/contracts.registry.json");
  assert.equal(
    registry.contracts.some(({ id }) => id === "translation-quality-workflow"),
    false,
  );

  const workflow = readText(".github/workflows/application-validate.yml");
  const packageJson = readText("package.json");
  for (const content of [workflow, packageJson]) {
    assert.doesNotMatch(content, /docs\/translation-profiles\/al-isabah\.md/);
  }
});

test("the consumer pin declares explicit upstream version compatibility", () => {
  const compatibility = readJson(compatibilityPath);
  assert.equal(
    compatibility.schema,
    "sabiqah.al-isabah-governance-compatibility.v1",
  );
  assert.equal(compatibility.consumerRole, "verified-application-consumer");
  assert.deepEqual(compatibility.upstream, {
    repository: "https://github.com/yaqub0r/al-isabah",
    commit: "9dfb8cea613329917ea9c932baaaef0bb842e966",
    referencePath: "docs/contracts/translation-governance-reference.v13.json",
    referenceVersion: "13.0.0",
    supportedReferenceMajor: 13,
    referenceSha256:
      "f5c0b4819939fadcd5808bec26fe345c9c868faddbf2b00556ecc0df02a175a5",
    textNormalization: "utf-8-lf",
  });
  assert.equal(
    Number(compatibility.upstream.referenceVersion.split(".")[0]),
    compatibility.upstream.supportedReferenceMajor,
  );
  assert.deepEqual(compatibility.distributionCompatibility, {
    activeSchemaVersion: "2.0.0",
    rollbackOnlySchemaVersion: "1.0.0",
  });
  assert.deepEqual(compatibility.releaseSemantics, {
    agentCompletionIndependentOfHumanReview: true,
    humanReviewScope: "append-only-per-record-metadata-and-confidence",
    humanReviewManagementState: "ongoing-nonterminal",
    humanReviewDisclosureRequired: true,
    humanReviewAffectsEligibility: false,
    humanReviewChangesReleaseClass: false,
    substantiveDefectsAffectEligibility: true,
    promotionEligibilityControls: [
      "source-binding",
      "provenance-binding",
      "rights-eligibility",
      "public-output-boundary",
      "deterministic-validation",
      "substantive-eligibility",
      "unresolved-state-disclosure",
    ],
    correctionMode: "new-immutable-release-with-supersession",
  });
});

test("the honorific adapter projection is bound to the upstream artifact", () => {
  const compatibility = readJson(compatibilityPath);
  const projection = readJson(projectionPath);
  const presentation = readJson(
    "packages/release-model/src/honorifics.presentation.json",
  );

  assert.equal(projection.role, "verified-consumer-projection");
  assert.equal(presentation.role, "consumer-presentation-only");
  assert.equal(projection.entries.length, 222);
  assert.equal(
    new Set(projection.entries.map(({ source }) => source)).size,
    projection.entries.length,
  );
  assert.deepEqual(projection.source, {
    repository: compatibility.upstream.repository,
    commit: compatibility.upstream.commit,
    referencePath: compatibility.upstream.referencePath,
    referenceVersion: compatibility.upstream.referenceVersion,
    referenceSha256: compatibility.upstream.referenceSha256,
    artifactPath: compatibility.formulaProjection.path,
    artifactVersion: compatibility.formulaProjection.artifactVersion,
    artifactSha256: compatibility.formulaProjection.artifactSha256,
    textNormalization: compatibility.upstream.textNormalization,
  });
});

test("verified ingestion and private-evidence consumer controls remain", () => {
  for (const path of [
    "scripts/verify_al_isabah_distribution.py",
    "scripts/verify_al_isabah_legacy_binding.py",
    ".github/workflows/ingest-al-isabah-distribution.yml",
    "docs/contracts/private-evidence-ingestion.md",
    "workers/platform/src/corpus.ts",
  ]) {
    assert.equal(existsSync(resolve(repoRoot, path)), true, path);
  }
});
