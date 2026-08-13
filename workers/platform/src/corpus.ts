import { json } from "./http";

export const CORPUS_ID = "al-isabah-public-openiti-5835c18-v6";
const CORPUS_PREFIX = `public-corpora/al-isabah/${CORPUS_ID}`;
const ITEM_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$/;

export interface CorpusMember {
  status: "active" | "limited" | "suspended";
}

export function corpusObjectKey(
  path: "summary" | "index" | "exclusions",
): string;
export function corpusObjectKey(path: "item", id: string): string;
export function corpusObjectKey(path: "section", id: string): string;
export function corpusObjectKey(
  path: "summary" | "index" | "exclusions" | "item" | "section",
  id?: string,
): string {
  if (path === "item") {
    if (!id || !ITEM_ID.test(id)) throw new Error("Invalid corpus item ID");
    return `${CORPUS_PREFIX}/items/${id}.json`;
  }
  if (path === "section") {
    if (!id || !ITEM_ID.test(id)) throw new Error("Invalid corpus section ID");
    return `${CORPUS_PREFIX}/sections/${id}.json`;
  }
  return `${CORPUS_PREFIX}/${path}.json`;
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
