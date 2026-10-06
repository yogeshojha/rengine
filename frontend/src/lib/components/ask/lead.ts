import type { BlockCauses } from '$lib/types/ask';

const LEAD = /^\s*(\d{1,3}(?:,\d{3})+|\d+)(\+?)(?=\s)/;

/** The count a text opens with, when it is the block's own count. */
export function leadNumber(
	text: string,
	total: number | null | undefined
): { number: string; rest: string } | null {
	if (total == null) return null;
	const found = LEAD.exec(text);
	if (!found || Number(found[1].replaceAll(',', '')) !== total) return null;
	return { number: `${found[1]}${found[2]}`, rest: text.slice(found[0].length).trimStart() };
}

export function causeLine(
	causes: BlockCauses | null | undefined,
	total: number | null | undefined,
	capped = false
): string | null {
	const top = causes?.groups[0];
	if (!causes || !top) return null;
	const n = causes.total_groups;
	if (n > 1) return `across ${n.toLocaleString()} ${causes.many}`;
	if (top.count === total && !capped) return `all on one ${causes.one}`;
	return `${top.count.toLocaleString()} on one ${causes.one}`;
}
