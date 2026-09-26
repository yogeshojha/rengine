/** The message a thrown value carries, or the fallback when it carries none. */
export function errorMessage(e: unknown, fallback: string): string {
	return e instanceof Error ? e.message : fallback;
}
