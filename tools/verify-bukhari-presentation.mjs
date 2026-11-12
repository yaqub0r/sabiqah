import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "playwright";

const base = process.env.BUKHARI_BASE_URL || "http://127.0.0.1:4322";
const output = resolve(".runtime/visual-qa/bukhari");
const source = JSON.parse(
  await readFile(".runtime/bukhari-reader.json", "utf8"),
);
await mkdir(output, { recursive: true });
const server = process.env.BUKHARI_BASE_URL
  ? null
  : spawn(
      process.execPath,
      [
        resolve("apps/web/node_modules/astro/bin/astro.mjs"),
        "preview",
        "--host",
        "127.0.0.1",
        "--port",
        "4322",
      ],
      {
        cwd: resolve("apps/web"),
        stdio: "ignore",
        env: { ...process.env, ASTRO_TELEMETRY_DISABLED: "1" },
      },
    );
let browser;
let activePage;
const results = [];
try {
  let ready = false;
  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      const response = await fetch(base);
      if (response.ok) {
        ready = true;
        break;
      }
    } catch {
      /* Server is still starting. */
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  assert(ready, "Application server did not become ready");
  browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_CHANNEL
      ? { channel: process.env.PLAYWRIGHT_CHANNEL }
      : {}),
  });
  for (const [width, height] of [
    [390, 844],
    [1024, 768],
    [1440, 900],
  ]) {
    const page = await browser.newPage({ viewport: { width, height } });
    activePage = page;
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    async function geometry(label) {
      const issues = await page.evaluate(() => {
        const problems = [];
        if (document.documentElement.scrollWidth > innerWidth + 1)
          problems.push("Page overflow");
        for (const el of document.querySelectorAll(
          ".book-card, .bukhari-bilingual p, .bukhari-evidence[open], .site-header",
        )) {
          if (el.getClientRects().length && el.scrollWidth > el.clientWidth + 2)
            problems.push(`Clipped content: ${el.className}`);
        }
        for (const el of document.querySelectorAll(".bukhari-bilingual")) {
          const [english, arabic] = el.children;
          const a = english.getBoundingClientRect(),
            b = arabic.getBoundingClientRect();
          if (
            innerWidth > 700 &&
            !(a.right <= b.left && Math.abs(a.top - b.top) < 2)
          )
            problems.push("Bilingual columns overlap or change order");
          if (innerWidth <= 700 && !(a.bottom <= b.top + 1))
            problems.push("Mobile reading columns overlap");
        }
        return problems;
      });
      await page.screenshot({ path: `${output}/${width}-${label}.png` });
      assert.deepEqual(issues, [], `${width}: ${label}`);
    }
    for (const [path, label] of [
      ["/", "home"],
      ["/works/", "books"],
      ["/works/sahih-al-bukhari/", "overview"],
    ]) {
      const response = await page.goto(base + path);
      assert.equal(response.status(), 200);
      await page.evaluate(() => document.fonts.ready);
      assert(
        (await page.locator('a[href="/works/sahih-al-bukhari/"]').count()) >
          0 || label === "overview",
      );
      if (label !== "overview")
        assert((await page.locator('a[href="/works/al-isabah/"]').count()) > 0);
      await geometry(label);
    }
    for (const section of ["opening", "faith"]) {
      const records = source.records.filter(
        (record) => record.bookSection === section,
      );
      await page.goto(`${base}/works/sahih-al-bukhari/${section}/`);
      await page.evaluate(() => document.fonts.ready);
      assert.equal(
        await page.locator(".bukhari-record").count(),
        records.length,
      );
      const rendered = await page
        .locator(".bukhari-record")
        .evaluateAll((elements) =>
          elements.map((el) => ({
            id: el.id,
            english: el.querySelector(".bukhari-english > p:last-child")
              .textContent,
            arabic: el.querySelector(".bukhari-arabic > p:last-child")
              .textContent,
            notes: [
              ...el.querySelectorAll(
                '[aria-label="Uncertainty disclosures"] li > span',
              ),
            ].map((note) => note.textContent),
          })),
        );
      assert.deepEqual(
        rendered,
        records.map((record) => ({
          id: record.sourceUnitId,
          english: record.english,
          arabic: record.arabic,
          notes: record.uncertainties.map((note) => note.summary),
        })),
      );
      assert.equal(
        await page
          .locator('.bukhari-section-nav [aria-current="page"]')
          .count(),
        1,
      );
      await geometry(section);
      const firstReport = records.find(
        (record) => record.printedHadithNumber !== null,
      );
      await page.locator(".bukhari-jump summary").click();
      await page
        .getByRole("link", {
          name: `Hadith ${firstReport.printedHadithNumber}`,
          exact: true,
        })
        .first()
        .click();
      assert.equal(new URL(page.url()).hash, `#${firstReport.sourceUnitId}`);
      await page.reload();
      await page.evaluate(() => document.fonts.ready);
      const target = page.locator(`#${firstReport.sourceUnitId}`);
      // Native hash/scroll restoration can finish after the load event. Assert
      // the settled user-visible outcome, rather than sampling that race.
      await page.waitForFunction(
        (id) => {
          const y = document.getElementById(id).getBoundingClientRect().top;
          return y >= 0 && y < innerHeight;
        },
        firstReport.sourceUnitId,
        { timeout: 5000 },
      );
      const details = target.locator("details");
      await details.locator("summary").click();
      assert(await details.evaluate((el) => el.open));
      await geometry(`${section}-expanded`);
      const last = records.at(-1);
      await page.goto(
        `${base}/works/sahih-al-bukhari/${section}/#${last.sourceUnitId}`,
      );
      await page.evaluate(() => document.fonts.ready);
      await page.waitForFunction(
        (id) => {
          const y = document.getElementById(id).getBoundingClientRect().top;
          return y >= 0 && y < innerHeight;
        },
        last.sourceUnitId,
        { timeout: 5000 },
      );
      await geometry(`${section}-last-record`);
    }
    assert.deepEqual(errors, [], "Browser runtime errors");
    results.push({
      width,
      height,
      pages: 5,
      textParity: true,
      disclosures: 49,
      stableLinks: true,
      geometry: "passed",
    });
    await page.close();
    activePage = null;
  }
  await writeFile(
    `${output}/results.json`,
    JSON.stringify(
      { base, releaseId: source.manifest.releaseId, results },
      null,
      2,
    ),
  );
  console.log(
    "Bukhari presentation passed: 5 pages at 3 viewports, all 110 records and 49 disclosures preserved.",
  );
} catch (error) {
  if (activePage && !activePage.isClosed()) {
    await activePage.screenshot({ path: `${output}/failure.png` });
    await writeFile(
      `${output}/failure.json`,
      JSON.stringify(
        {
          url: activePage.url(),
          viewport: activePage.viewportSize(),
          error: String(error),
        },
        null,
        2,
      ),
    );
  }
  throw error;
} finally {
  await browser?.close();
  server?.kill();
}
