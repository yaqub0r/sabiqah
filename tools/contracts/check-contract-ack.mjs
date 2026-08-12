#!/usr/bin/env node

import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = resolve(SCRIPT_DIR, "../..");
export const REGISTRY_PATH = resolve(
  REPO_ROOT,
  "docs/contracts/contracts.registry.json",
);

export function normalizePath(value) {
  return value.replaceAll("\\", "/").replace(/^\.\//, "");
}

export function globToRegExp(pattern) {
  const normalized = normalizePath(pattern);
  let expression = "^";

  for (let index = 0; index < normalized.length; index += 1) {
    const character = normalized[index];
    const next = normalized[index + 1];

    if (character === "*" && next === "*") {
      expression += ".*";
      index += 1;
    } else if (character === "*") {
      expression += "[^/]*";
    } else if (character === "?") {
      expression += "[^/]";
    } else {
      expression += character.replace(/[|\\{}()[\]^$+?.]/g, "\\$&");
    }
  }

  return new RegExp(`${expression}$`);
}

export function validateRegistry(registry, fileExists = () => true) {
  const errors = [];
  const ids = new Set();

  if (registry?.schemaVersion !== 1) {
    errors.push("Registry schemaVersion must be 1.");
  }
  if (!Array.isArray(registry?.contracts) || registry.contracts.length === 0) {
    errors.push("Registry must contain at least one contract.");
    return errors;
  }

  for (const contract of registry.contracts) {
    if (!contract?.id || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(contract.id)) {
      errors.push(`Invalid contract id: ${String(contract?.id)}`);
    } else if (ids.has(contract.id)) {
      errors.push(`Duplicate contract id: ${contract.id}`);
    } else {
      ids.add(contract.id);
    }

    if (contract?.status !== "active") {
      errors.push(`Contract ${String(contract?.id)} must have active status.`);
    }
    if (!contract?.contractPath || !fileExists(contract.contractPath)) {
      errors.push(
        `Contract ${String(contract?.id)} document is missing: ${String(contract?.contractPath)}`,
      );
    }
    if (!Array.isArray(contract?.paths) || contract.paths.length === 0) {
      errors.push(
        `Contract ${String(contract?.id)} must govern at least one path.`,
      );
    } else {
      for (const pattern of contract.paths) {
        if (
          typeof pattern !== "string" ||
          pattern.length === 0 ||
          pattern.startsWith("/") ||
          pattern.includes("..") ||
          pattern.includes("\\")
        ) {
          errors.push(
            `Contract ${String(contract?.id)} has invalid path pattern: ${String(pattern)}`,
          );
        }
      }
    }
  }

  return errors;
}

export function requiredContracts(files, registry) {
  const required = new Set();
  const reasons = new Map();

  for (const contract of registry.contracts) {
    const matchers = contract.paths.map(globToRegExp);
    const matched = files
      .map(normalizePath)
      .filter((file) => matchers.some((matcher) => matcher.test(file)));

    if (matched.length > 0) {
      required.add(contract.id);
      reasons.set(contract.id, matched);
    }
  }

  return { required, reasons };
}

export function parseAcknowledgements(body, registry) {
  const knownIds = new Set(registry.contracts.map((contract) => contract.id));
  const lines = body.split(/\r?\n/);
  const headingIndex = lines.findIndex((line) =>
    /^##\s+Contracts consulted\s*$/i.test(line),
  );

  if (headingIndex === -1) {
    return { acknowledged: new Set(), noneRequired: false, unknown: new Set() };
  }

  const sectionLines = [];
  for (const line of lines.slice(headingIndex + 1)) {
    if (/^##\s+/.test(line)) break;
    sectionLines.push(line);
  }
  const section = sectionLines.join("\n");

  const acknowledged = new Set();
  const unknown = new Set();
  const noneRequired = /^\s*[-*]\s*\[[xX]\]\s*None required\s*$/im.test(
    section,
  );
  const idPattern =
    /^\s*[-*]\s*(?:\[[ xX]\]\s*)?`([a-z0-9]+(?:-[a-z0-9]+)*)`\s*$/gim;

  for (const match of section.matchAll(idPattern)) {
    if (knownIds.has(match[1])) {
      acknowledged.add(match[1]);
    } else if (match[1] !== "contract-id") {
      unknown.add(match[1]);
    }
  }

  return { acknowledged, noneRequired, unknown };
}

export function evaluateAcknowledgements(files, body, registry) {
  const { required, reasons } = requiredContracts(files, registry);
  const { acknowledged, noneRequired, unknown } = parseAcknowledgements(
    body,
    registry,
  );
  const missing = new Set([...required].filter((id) => !acknowledged.has(id)));
  const errors = [];

  if (unknown.size > 0) {
    errors.push(`Unknown contract ids: ${[...unknown].sort().join(", ")}`);
  }
  if (missing.size > 0) {
    errors.push(`Missing contract ids: ${[...missing].sort().join(", ")}`);
  }
  if (required.size > 0 && noneRequired) {
    errors.push("None required is checked, but governed paths changed.");
  }

  return {
    required,
    reasons,
    acknowledged,
    noneRequired,
    unknown,
    missing,
    errors,
  };
}

function loadRegistry() {
  return JSON.parse(readFileSync(REGISTRY_PATH, "utf8"));
}

function changedFiles(base, head) {
  const result = spawnSync(
    "git",
    ["diff", "--name-only", `${base}...${head}`],
    { cwd: REPO_ROOT, encoding: "utf8" },
  );

  if (result.status !== 0) {
    throw new Error(
      result.stderr.trim() || "Unable to determine changed files.",
    );
  }

  return result.stdout.split(/\r?\n/).filter(Boolean);
}

function main() {
  const registry = loadRegistry();
  const registryErrors = validateRegistry(registry, (path) => {
    try {
      readFileSync(resolve(REPO_ROOT, normalizePath(path)));
      return true;
    } catch {
      return false;
    }
  });

  if (registryErrors.length > 0) {
    for (const error of registryErrors) console.error(error);
    return 1;
  }

  const base = process.env.CONTRACT_ACK_BASE_SHA;
  const head = process.env.CONTRACT_ACK_HEAD_SHA;
  const body = process.env.PR_BODY ?? "";

  if (!base || !head) {
    console.error(
      "CONTRACT_ACK_BASE_SHA and CONTRACT_ACK_HEAD_SHA are required.",
    );
    return 1;
  }

  const files = changedFiles(base, head);
  const result = evaluateAcknowledgements(files, body, registry);

  if (result.errors.length > 0) {
    for (const error of result.errors) console.error(error);
    for (const id of [...result.required].sort()) {
      console.error(`Required ${id}:`);
      for (const file of result.reasons.get(id) ?? []) {
        console.error(`  - ${file}`);
      }
    }
    console.error("Read docs/contracts/INDEX.md and update the PR body.");
    return 1;
  }

  if (result.required.size === 0) {
    console.log("No governed contract surfaces changed.");
  } else {
    console.log("Required contract acknowledgements are present:");
    for (const id of [...result.required].sort()) console.log(`  - ${id}`);
  }
  return 0;
}

if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  process.exitCode = main();
}
