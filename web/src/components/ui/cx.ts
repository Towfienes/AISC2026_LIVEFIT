/** Tiny class joiner — avoids a clsx dependency for a 3-line need. */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
