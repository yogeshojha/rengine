<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import type { QueryProblem, QueryToken, TokenKind } from '$lib/utilities/query-lexer';

	interface Props {
		source: string;
		tokens: QueryToken[];
		problems: QueryProblem[];
	}

	let { source, tokens, problems }: Props = $props();

	const TONE: Record<string, string> = {
		field: 'text-primary',
		operator: 'text-primary/70',
		value: 'text-foreground',
		term: 'text-foreground',
		connector: 'font-semibold text-info',
		paren: 'text-muted-foreground',
		space: '',
		invalid: 'text-destructive'
	};
	const FLAW: Record<string, string> = {
		error: 'underline decoration-destructive decoration-wavy underline-offset-4',
		warning: 'underline decoration-warning decoration-dotted underline-offset-4'
	};
	const KEY_KINDS = new Set<TokenKind>(['field', 'operator']);

	interface Segment {
		text: string;
		kind: TokenKind;
		tone: string;
		flaw: string;
	}
	interface Run {
		key: boolean;
		segments: Segment[];
	}

	let runs = $derived.by<Run[]>(() => {
		const edges = new SvelteSet<number>([0, source.length]);
		for (const t of tokens) {
			edges.add(t.start);
			edges.add(t.end);
		}
		for (const p of problems) {
			edges.add(p.start);
			edges.add(p.end);
		}
		const points = [...edges].filter((n) => n >= 0 && n <= source.length).sort((a, b) => a - b);
		const out: Run[] = [];
		for (let i = 0; i < points.length - 1; i += 1) {
			const from = points[i];
			const to = points[i + 1];
			if (to <= from) continue;
			const token = tokens.find((t) => t.start <= from && t.end >= to);
			const problem = problems.find((p) => p.start <= from && p.end >= to);
			const kind = token?.kind ?? 'term';
			const segment: Segment = {
				text: source.slice(from, to),
				kind,
				tone: TONE[kind] ?? '',
				flaw: problem ? (FLAW[problem.level] ?? '') : ''
			};
			const key = KEY_KINDS.has(kind) && !problem;
			const last = out.at(-1);
			if (key && last?.key) last.segments.push(segment);
			else out.push({ key, segments: [segment] });
		}
		return out;
	});
</script>

{#each runs as run, i (i)}<span class={run.key ? 'query-key' : ''}
		>{#each run.segments as segment, j (j)}<span class="{segment.tone} {segment.flaw}"
				>{segment.text}</span
			>{/each}</span
	>{/each}

<style>
	.query-key {
		border-radius: 3px;
		padding-block: 1px;
		background: color-mix(in oklch, var(--primary) 11%, transparent);
		box-shadow: 0 0 0 2px color-mix(in oklch, var(--primary) 11%, transparent);
	}
</style>
