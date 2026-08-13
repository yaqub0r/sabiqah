import assert from "node:assert/strict";
import {
  lstat,
  mkdir,
  mkdtemp,
  readFile,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { cleanupGenerated } from "./cleanup-generated.mjs";

async function exists(target) {
  try {
    await lstat(target);
    return true;
  } catch (error) {
    if (error?.code === "ENOENT") {
      return false;
    }
    throw error;
  }
}

async function createRepository(parent, name = "sabiqah") {
  const root = path.join(parent, "repository");
  await mkdir(path.join(root, ".git"), { recursive: true });
  await writeFile(
    path.join(root, "package.json"),
    `${JSON.stringify({ name, private: true }, null, 2)}\n`,
  );
  await writeFile(path.join(root, "source.txt"), "keep\n");
  return root;
}

test("dry run is inert and apply removes only generated dependency roots", async () => {
  const parent = await mkdtemp(path.join(os.tmpdir(), "sabiqah-cleanup-"));
  try {
    const root = await createRepository(parent);
    const outside = path.join(parent, "outside");
    await mkdir(outside);
    await writeFile(path.join(outside, "sentinel.txt"), "keep\n");

    const targets = [
      path.join(root, ".pnpm"),
      path.join(root, "node_modules"),
      path.join(root, "apps", "web", "node_modules"),
    ];
    for (const target of targets) {
      await mkdir(target, { recursive: true });
      await writeFile(path.join(target, "generated.txt"), "remove\n");
    }

    const externalLink = path.join(targets[2], "external-link");
    await symlink(
      outside,
      externalLink,
      process.platform === "win32" ? "junction" : "dir",
    );

    const dryRunTargets = await cleanupGenerated({
      root,
      apply: false,
      log: () => {},
    });
    assert.deepEqual(new Set(dryRunTargets), new Set(targets));
    for (const target of targets) {
      assert.equal(await exists(target), true);
    }

    const removedTargets = await cleanupGenerated({
      root,
      apply: true,
      log: () => {},
    });
    assert.deepEqual(new Set(removedTargets), new Set(targets));
    for (const target of targets) {
      assert.equal(await exists(target), false);
    }
    assert.equal(
      await readFile(path.join(outside, "sentinel.txt"), "utf8"),
      "keep\n",
    );
    assert.equal(
      await readFile(path.join(root, "source.txt"), "utf8"),
      "keep\n",
    );
  } finally {
    await rm(parent, { force: true, recursive: true });
  }
});

test("cleanup rejects a generated root that is a symbolic link", async () => {
  const parent = await mkdtemp(path.join(os.tmpdir(), "sabiqah-cleanup-"));
  try {
    const root = await createRepository(parent);
    const outside = path.join(parent, "outside");
    await mkdir(outside);
    await writeFile(path.join(outside, "sentinel.txt"), "keep\n");
    await symlink(
      outside,
      path.join(root, ".pnpm"),
      process.platform === "win32" ? "junction" : "dir",
    );

    await assert.rejects(
      cleanupGenerated({ root, apply: true, log: () => {} }),
      /Refusing symbolic-link cleanup root/,
    );
    assert.equal(
      await readFile(path.join(outside, "sentinel.txt"), "utf8"),
      "keep\n",
    );
  } finally {
    await rm(parent, { force: true, recursive: true });
  }
});

test("cleanup rejects a directory that is not the Sabiqah repository", async () => {
  const parent = await mkdtemp(path.join(os.tmpdir(), "sabiqah-cleanup-"));
  try {
    const root = await createRepository(parent, "not-sabiqah");
    await mkdir(path.join(root, "node_modules"));

    await assert.rejects(
      cleanupGenerated({ root, apply: true, log: () => {} }),
      /Refusing cleanup outside the sabiqah repository/,
    );
    assert.equal(await exists(path.join(root, "node_modules")), true);
  } finally {
    await rm(parent, { force: true, recursive: true });
  }
});
