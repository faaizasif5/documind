/** Topic-agnostic starters so suggestions stay useful for any PDF. */
export const STARTER_PROMPT_TEMPLATES: readonly string[] = [
  "Summarize {document} in a few bullet points.",
  "What are the main topics covered in {document}?",
  "What are the most important details in {document}?",
];

function withoutExtension(filename: string): string {
  return filename.replace(/\.pdf$/i, "");
}

/**
 * Builds starter questions from the user's own documents, cycling through them
 * so a single-document library still gets varied suggestions.
 */
export function buildStarterPrompts(filenames: readonly string[]): string[] {
  if (filenames.length === 0) {
    return [];
  }
  return STARTER_PROMPT_TEMPLATES.map((template, index) =>
    template.replace(
      "{document}",
      withoutExtension(filenames[index % filenames.length]),
    ),
  );
}
