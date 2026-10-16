// Plain-English names for codes that come from the API.

const QTYPE: Record<string, string> = {
  tfng: "True / False / Not given",
  ynng: "Yes / No / Not given",
  mcq: "Multiple choice",
};
const CHOICE: Record<string, string> = { T: "TRUE", F: "FALSE", NG: "NOT GIVEN", Y: "YES", N: "NO" };

export const sentence = (s: string) => s[0].toUpperCase() + s.slice(1).replaceAll("_", " ");

export const qtypeLabel = (t: string) => QTYPE[t] ?? sentence(t);

/** "tfng:NG→T" → "NOT GIVEN read as TRUE"; "wrong_word" → "Wrong word". */
export function errorLabel(e: string | null) {
  const m = e?.match(/^\w+:(\w+)→(\w+)$/);
  if (m) return `${CHOICE[m[1]]} read as ${CHOICE[m[2]]}`;
  return e ? sentence(e) : "Wrong";
}
