import { BLOCK_REF, StreamEvent, TraceStatus } from '$lib/config/ask';
import type { AnswerBlock, AskTraceStep, BlockData, EstateStreamFrame } from '$lib/types/ask';

export interface Draft {
	question: string;
	about: string | null;
	intelligent: boolean;
	kept: string;
	said: string;
	trace: AskTraceStep[];
	blocks: AnswerBlock[];
}

const CITES = new RegExp(BLOCK_REF.source);
const OPEN_REF = /\[B?\d{0,2}$/;

export function newDraft(question: string, about: string | null, intelligent: boolean): Draft {
	return { question, about, intelligent, kept: '', said: '', trace: [], blocks: [] };
}

/** The draft's text, without a block reference still being typed. */
export function draftText(draft: Draft): string {
	return `${draft.kept}${draft.said}`.replace(OPEN_REF, '').trim();
}

const PARAGRAPH = /\n\s*\n/;
const NARRATION =
	/^(now|next|then|let me|let's|i'll|i will|i am|i'm|checking|looking|searching)\b|:$/i;

/** Text written before a tool call stays only when it cites a block, without narration. */
function settleRound(draft: Draft): Draft {
	if (!draft.said || !CITES.test(draft.said)) return { ...draft, said: '' };
	const parts = draft.said.split(PARAGRAPH).filter((p) => p.trim());
	const kept = parts.filter((p) => CITES.test(p) || !NARRATION.test(p.trim()));
	const text =
		kept.length === parts.length
			? draft.said
			: kept.length
				? `${kept.map((p) => p.trim()).join('\n\n')}\n\n`
				: '';
	return { ...draft, kept: `${draft.kept}${text}`, said: '' };
}

export function applyFrame(
	draft: Draft,
	frame: EstateStreamFrame
): { draft: Draft; data?: BlockData } {
	switch (frame.event) {
		case StreamEvent.TRACE: {
			const { index, ...step } = frame.data;
			const next = step.status === TraceStatus.RUNNING ? settleRound(draft) : draft;
			const trace = [...next.trace];
			trace[index] = step;
			return { draft: { ...next, trace } };
		}
		case StreamEvent.DELTA:
			return { draft: { ...draft, said: draft.said + frame.data.text } };
		case StreamEvent.BLOCK:
			return {
				draft: { ...draft, blocks: [...draft.blocks, frame.data.block] },
				data: frame.data.data
			};
		default:
			return { draft };
	}
}
