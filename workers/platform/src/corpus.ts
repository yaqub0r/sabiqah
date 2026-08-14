import { json } from "./http";

export const LEGACY_CORPUS_ID = "al-isabah-public-openiti-5835c18-v11";
export const CORPUS_POINTER_KEY = "public-corpora/al-isabah/current.json";
const ITEM_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$/;
const CORPUS_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$/;

export interface CorpusContext {
  id: string;
  prefix: string;
}

export const LEGACY_CORPUS_CONTEXT: CorpusContext = {
  id: LEGACY_CORPUS_ID,
  prefix: `public-corpora/al-isabah/${LEGACY_CORPUS_ID}`,
};

interface CorpusPointer {
  schemaVersion: "1.0.0";
  corpusId: string;
  prefix: string;
}

export interface CorpusMember {
  status: "active" | "limited" | "suspended";
}

export function corpusObjectKey(
  context: CorpusContext,
  path: "summary" | "index" | "exclusions",
): string;
export function corpusObjectKey(
  context: CorpusContext,
  path: "item",
  id: string,
): string;
export function corpusObjectKey(
  context: CorpusContext,
  path: "section",
  id: string,
): string;
export function corpusObjectKey(
  context: CorpusContext,
  path: "summary" | "index" | "exclusions" | "item" | "section",
  id?: string,
): string {
  if (path === "item") {
    if (!id || !ITEM_ID.test(id)) throw new Error("Invalid corpus item ID");
    return `${context.prefix}/items/${id}.json`;
  }
  if (path === "section") {
    if (!id || !ITEM_ID.test(id)) throw new Error("Invalid corpus section ID");
    return `${context.prefix}/sections/${id}.json`;
  }
  return `${context.prefix}/${path}.json`;
}

export async function resolveCorpusContext(
  bucket: R2Bucket,
): Promise<CorpusContext> {
  const object = await bucket.get(CORPUS_POINTER_KEY);
  if (!object) return LEGACY_CORPUS_CONTEXT;
  let pointer: Partial<CorpusPointer>;
  try {
    pointer = JSON.parse(await object.text()) as Partial<CorpusPointer>;
  } catch {
    throw new Error("Active corpus pointer is invalid");
  }
  if (
    pointer.schemaVersion !== "1.0.0" ||
    typeof pointer.corpusId !== "string" ||
    !CORPUS_ID.test(pointer.corpusId) ||
    pointer.prefix !== `public-corpora/al-isabah/${pointer.corpusId}`
  )
    throw new Error("Active corpus pointer is inconsistent");
  return { id: pointer.corpusId, prefix: pointer.prefix };
}

export function canReviewCorpus(member: CorpusMember | null): boolean {
  return member?.status === "active";
}

export async function corpusJson(
  bucket: R2Bucket,
  key: string,
): Promise<Response> {
  const object = await bucket.get(key);
  if (!object)
    return json({ error: "Review corpus is not available." }, { status: 503 });
  return new Response(object.body, {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "public, max-age=300, s-maxage=3600",
      "x-content-type-options": "nosniff",
    },
  });
}
