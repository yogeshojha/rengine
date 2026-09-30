export type AnswerSpan =
	| { kind: 'text' | 'bold' | 'code'; text: string }
	| { kind: 'cite'; n: number };

export interface AnswerBlock {
	kind: 'p' | 'item';
	n: number | null;
	spans: AnswerSpan[];
}

const ITEM = /^\s*(?:(\d{1,2})[.)]|[-*•])\s+(.*)$/;
const TOKEN = /(\[\[(\d{1,2})\]\])|(\*\*([^*]+)\*\*)|(`([^`]+)`)/g;

export function spans(text: string): AnswerSpan[] {
	const out: AnswerSpan[] = [];
	let last = 0;
	for (const m of text.matchAll(TOKEN)) {
		const at = m.index ?? 0;
		if (at > last) out.push({ kind: 'text', text: text.slice(last, at) });
		if (m[2]) out.push({ kind: 'cite', n: Number(m[2]) });
		else if (m[4]) out.push({ kind: 'bold', text: m[4] });
		else if (m[6]) out.push({ kind: 'code', text: m[6] });
		last = at + m[0].length;
	}
	if (last < text.length) out.push({ kind: 'text', text: text.slice(last) });
	return out;
}

export function parseAnswer(text: string): AnswerBlock[] {
	const blocks: AnswerBlock[] = [];
	let para: string[] = [];
	const flush = () => {
		if (!para.length) return;
		blocks.push({ kind: 'p', n: null, spans: spans(para.join(' ')) });
		para = [];
	};
	for (const raw of text.split('\n')) {
		const line = raw.trim();
		if (!line) {
			flush();
			continue;
		}
		const item = ITEM.exec(line);
		if (item) {
			flush();
			blocks.push({ kind: 'item', n: item[1] ? Number(item[1]) : null, spans: spans(item[2]) });
			continue;
		}
		para.push(line);
	}
	flush();
	return blocks;
}

export function cited(blocks: AnswerBlock[]): number[] {
	const seen = new Set<number>();
	for (const b of blocks) for (const s of b.spans) if (s.kind === 'cite') seen.add(s.n);
	return [...seen];
}
