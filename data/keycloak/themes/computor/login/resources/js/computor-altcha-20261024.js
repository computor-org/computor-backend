import "./altcha-3.0.11.min.js";
import "./altcha-de-3.0.11.js";

// The vendored German strings address the visitor with "Sie"; the rest of
// Computor says "du" (issues#478). Override only those, leaving the vendored
// file untouched so its checksum in altcha-manifest.json still holds. The file
// name carries a date because theme resources are cached for 30 days.
if ("$altcha" in globalThis) {
  const de = globalThis.$altcha.i18n.get("de") || {};
  globalThis.$altcha.i18n.set("de", {
    ...de,
    enterCodeAria: "Gib den Code ein, den du hörst. Mit der Leertaste spielst du die Audiodatei ab.",
    error: "Die Prüfung ist fehlgeschlagen. Bitte versuch es später noch einmal.",
    expired: "Die Prüfung ist abgelaufen. Bitte versuch es noch einmal.",
    enterCodeFromImage: "Gib bitte den Code aus dem Bild unten ein, um fortzufahren.",
  });
}
