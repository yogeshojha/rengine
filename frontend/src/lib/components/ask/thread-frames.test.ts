import { describe, expect, it } from 'vitest';
import { applyFrame, draftText, newDraft } from './thread-frames';
import type { AnswerBlock, BlockData } from '$lib/types/ask';

const block: AnswerBlock = {
	id: 'B1',
	kind: 'rows',
	dimension: 'web_assets',
	query: 'tech:wordpress',
	group_by: null,
	cve: null,
	title: null,
	total: 9,
	capped: false,
	about: null,
	edited: false
};

const data: BlockData = {
	id: 'B1',
	kind: 'rows',
	dimension: 'web_assets',
	total: 9,
	capped: false,
	rows: [],
	groups: [],
	covered: 3,
	record: null,
	scope_values: [],
	error: null
};

const running = { index: 0, tool: 'show_rows', label: 'Show rows', status: 'running' } as const;

describe('estate stream frames', () => {
	it('drops narration written before a tool call', () => {
		let draft = newDraft('Which run WordPress', null, false);
		draft = applyFrame(draft, { event: 'delta', data: { text: "I'll search." } }).draft;
		draft = applyFrame(draft, { event: 'trace', data: running as never }).draft;
		draft = applyFrame(draft, { event: 'delta', data: { text: '9 web assets [B1].' } }).draft;
		expect(draftText(draft)).toBe('9 web assets [B1].');
	});

	it('keeps text before a tool call when it cites a block', () => {
		let draft = newDraft('q', null, true);
		draft = applyFrame(draft, { event: 'delta', data: { text: 'Yes, 2 of 9 [B1]. ' } }).draft;
		draft = applyFrame(draft, { event: 'trace', data: running as never }).draft;
		draft = applyFrame(draft, { event: 'delta', data: { text: 'None are KEV [B2].' } }).draft;
		expect(draftText(draft)).toBe('Yes, 2 of 9 [B1]. None are KEV [B2].');
	});

	it('drops a narration paragraph from text that cites a block', () => {
		let draft = newDraft('q', null, true);
		const said = '240 services [B1].\n\nNow checking for critical exposures:';
		draft = applyFrame(draft, { event: 'delta', data: { text: said } }).draft;
		draft = applyFrame(draft, { event: 'trace', data: running as never }).draft;
		draft = applyFrame(draft, { event: 'delta', data: { text: 'None are KEV [B2].' } }).draft;
		expect(draftText(draft)).toBe('240 services [B1].\n\nNone are KEV [B2].');
	});

	it('hides a block reference still arriving', () => {
		let draft = newDraft('q', null, false);
		draft = applyFrame(draft, { event: 'delta', data: { text: '9 web assets [B' } }).draft;
		expect(draftText(draft)).toBe('9 web assets');
	});

	it('collects a block and its data', () => {
		const { draft, data: got } = applyFrame(newDraft('q', null, false), {
			event: 'block',
			data: { block, data }
		});
		expect(draft.blocks.map((b) => b.id)).toEqual(['B1']);
		expect(got?.total).toBe(9);
	});
});
