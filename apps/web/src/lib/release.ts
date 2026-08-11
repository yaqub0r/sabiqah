import fixture from "../../../../fixtures/releases/al-isabah-beta-v1.json";
import { parseBookRelease } from "@sabiqah/release-model";

export const alIsabahRelease = parseBookRelease(fixture);
