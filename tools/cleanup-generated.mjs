import { lstat, readFile, readdir, realpath, rm } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const PROJECT_NAME = "sabiqah";
const ROOT_GENERATED_DIRECTORIES = [".pnpm", "node_modules"];
const WORKSPACE_CONTAINERS = ["apps", "packages", "workers"];

async function lstatIfPresent(target) {
  try {
    return await lstat(target);
  } catch (error) {
    if (error?.code === "ENOENT") {
      return null;
    }
    throw error;
  }
}

function isWithin(parent, candidate) {
  const relative = path.relative(parent, candidate);
  return (
    relative === "" ||
    (!relative.startsWith(`..${path.sep}`) &&
      relative !== ".." &&
      !path.isAbsolute(relative))
  );
}

async function validateRepositoryRoot(root) {
  const absoluteRoot = path.resolve(root);
  const packagePath = path.join(absoluteRoot, "package.json");
  const packageDocument = JSON.parse(await readFile(packagePath, "utf8"));

  if (packageDocument.name !== PROJECT_NAME) {
    throw new Error(
      `Refusing cleanup outside the ${PROJECT_NAME} repository: ${absoluteRoot}`,
    );
  }

  const gitMarker = await lstatIfPresent(path.join(absoluteRoot, ".git"));
  if (!gitMarker || (!gitMarker.isDirectory() && !gitMarker.isFile())) {
    throw new Error(`Refusing cleanup without a .git marker: ${absoluteRoot}`);
  }

  return {
    absoluteRoot,
    realRoot: await realpath(absoluteRoot),
  };
}

async function validateGeneratedDirectory(repository, target) {
  const relative = path.relative(repository.absoluteRoot, target);
  if (
    relative === "" ||
    relative === ".." ||
    relative.startsWith(`..${path.sep}`) ||
    path.isAbsolute(relative)
  ) {
    throw new Error(
      `Generated cleanup target escaped the repository: ${target}`,
    );
  }

  const status = await lstatIfPresent(target);
  if (!status) {
    return false;
  }
  if (status.isSymbolicLink()) {
    throw new Error(`Refusing symbolic-link cleanup root: ${target}`);
  }
  if (!status.isDirectory()) {
    throw new Error(`Generated cleanup target is not a directory: ${target}`);
  }

  const realParent = await realpath(path.dirname(target));
  if (!isWithin(repository.realRoot, realParent)) {
    throw new Error(
      `Generated cleanup parent escaped the repository: ${target}`,
    );
  }

  return true;
}

async function collectGeneratedDirectories(repository) {
  const candidates = ROOT_GENERATED_DIRECTORIES.map((name) =>
    path.join(repository.absoluteRoot, name),
  );

  for (const containerName of WORKSPACE_CONTAINERS) {
    const container = path.join(repository.absoluteRoot, containerName);
    const containerStatus = await lstatIfPresent(container);
    if (!containerStatus) {
      continue;
    }
    if (containerStatus.isSymbolicLink() || !containerStatus.isDirectory()) {
      throw new Error(`Refusing unexpected workspace container: ${container}`);
    }

    for (const entry of await readdir(container, { withFileTypes: true })) {
      if (!entry.isDirectory() || entry.isSymbolicLink()) {
        continue;
      }
      candidates.push(path.join(container, entry.name, "node_modules"));
    }
  }

  const targets = [];
  for (const candidate of candidates) {
    if (await validateGeneratedDirectory(repository, candidate)) {
      targets.push(candidate);
    }
  }

  return targets.sort((left, right) => right.length - left.length);
}

export async function cleanupGenerated({
  root = process.cwd(),
  apply = false,
  log = console.log,
} = {}) {
  const repository = await validateRepositoryRoot(root);
  const targets = await collectGeneratedDirectories(repository);

  if (targets.length === 0) {
    log("No generated dependency directories found.");
    return [];
  }

  for (const target of targets) {
    const relative = path.relative(repository.absoluteRoot, target);
    log(`${apply ? "Removing" : "Would remove"}: ${relative}`);
  }

  if (!apply) {
    log("Dry run only. Re-run with --apply after reviewing every target.");
    return targets;
  }

  for (const target of targets) {
    await rm(target, { force: false, maxRetries: 0, recursive: true });
    if (await lstatIfPresent(target)) {
      throw new Error(`Generated directory remains after cleanup: ${target}`);
    }
  }

  log(`Removed ${targets.length} generated dependency directories.`);
  return targets;
}

async function runCli() {
  const arguments_ = process.argv.slice(2);
  const unknown = arguments_.filter((argument) => argument !== "--apply");
  if (unknown.length > 0) {
    throw new Error(`Unknown argument(s): ${unknown.join(", ")}`);
  }

  await cleanupGenerated({ apply: arguments_.includes("--apply") });
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : "";
if (invokedPath === fileURLToPath(import.meta.url)) {
  runCli().catch((error) => {
    console.error(`[cleanup:generated] ${error.message}`);
    process.exitCode = 1;
  });
}
