import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { resolve } from "node:path";

import {
  REGISTRY_PATH,
  REPO_ROOT,
  evaluateAcknowledgements,
  globToRegExp,
  parseAcknowledgements,
  requiredContracts,
  validateRegistry,
} from "./check-contract-ack.mjs";

const registry = JSON.parse(readFileSync(REGISTRY_PATH, "utf8"));

test("registry is internally valid and every contract document exists", () => {
  const errors = validateRegistry(registry, (path) => {
    try {
      readFileSync(resolve(REPO_ROOT, path));
      return true;
    } catch {
      return false;
    }
  });
  assert.deepEqual(errors, []);
});

test("glob matching respects directory boundaries", () => {
  const matcher = globToRegExp("packages/release-model/**");
  assert.equal(matcher.test("packages/release-model/src/index.ts"), true);
  assert.equal(matcher.test("packages/editor/src/index.ts"), false);
});

test("release fixtures require all scholarly-content contracts", () => {
  const { required } = requiredContracts(
    ["fixtures/releases/al-isabah-beta-v1.json"],
    registry,
  );
  assert.deepEqual([...required].sort(), [
    "canonical-book-promotion",
    "content-source-compliance",
    "translation-quality-workflow",
  ]);
});

test("translation implementation paths require the quality contract", () => {
  const { required } = requiredContracts(
    [
      "docs/translation-profiles/al-isabah.md",
      "scripts/translation/run_book_pipeline.py",
      "workers/platform/tests/translationReviews.test.ts",
    ],
    registry,
  );
  assert.deepEqual([...required], ["translation-quality-workflow"]);
});

test("acknowledgements are read only from the contract section", () => {
  const parsed = parseAcknowledgements(
    `## Contracts consulted

- [x] I read the contracts.
- [ ] None required
- \`content-source-compliance\`

## Notes

- \`canonical-book-promotion\`
`,
    registry,
  );
  assert.deepEqual([...parsed.acknowledged], ["content-source-compliance"]);
  assert.equal(parsed.noneRequired, false);
});

test("all required acknowledgements pass", () => {
  const result = evaluateAcknowledgements(
    ["docs/contracts/INDEX.md"],
    `## Contracts consulted

- [x] I read the contracts.
- [ ] None required
- \`content-source-compliance\`
- \`canonical-book-promotion\`
- \`translation-quality-workflow\`
`,
    registry,
  );
  assert.deepEqual(result.errors, []);
});

test("a missing required contract fails", () => {
  const result = evaluateAcknowledgements(
    ["docs/contracts/INDEX.md"],
    `## Contracts consulted

- \`content-source-compliance\`
`,
    registry,
  );
  assert.deepEqual(
    [...result.missing],
    ["canonical-book-promotion", "translation-quality-workflow"],
  );
  assert.match(result.errors.join("\n"), /Missing contract ids/);
});

test("none required fails for governed changes", () => {
  const result = evaluateAcknowledgements(
    ["scripts/acquisition/import-witness.mjs"],
    `## Contracts consulted

- [x] None required
- \`content-source-compliance\`
`,
    registry,
  );
  assert.match(result.errors.join("\n"), /None required is checked/);
});

test("unknown contract ids fail", () => {
  const result = evaluateAcknowledgements(
    ["README.md"],
    `## Contracts consulted

- \`not-a-real-contract\`
`,
    registry,
  );
  assert.deepEqual([...result.unknown], ["not-a-real-contract"]);
  assert.match(result.errors.join("\n"), /Unknown contract ids/);
});
