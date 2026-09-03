<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import type { QueryProblem, QueryToken } from '$lib/utilities/query-lexer';

	interface Props {
		source: string;
		tokens: QueryToken[];
		problems: QueryProblem[];
	}

	let { source, tokens, problems }: Props = $props();

	const TONE: Record<string, string> = {
		field: 'text-primary',
		operator: 'text-muted-foreground',
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

	interface Segment {
		text: string;
		tone: string;
		flaw: string;
	}

	let segments = $derived.by<Segment[]>(() => {
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
		const out: Segment[] = [];
		for (let i = 0; i < points.length - 1; i += 1) {
			const from = points[i];
			const to = points[i + 1];
			if (to <= from) continue;
			const token = tokens.find((t) => t.start <= from && t.end >= to);
			const problem = problems.find((p) => p.start <= from && p.end >= to);
			out.push({
				text: source.slice(from, to),
				tone: TONE[token?.kind ?? 'term'] ?? '',
				flaw: problem ? (FLAW[problem.level] ?? '') : ''
			});
		}
		return out;
	});
</script>

{#each segments as segment, i (i)}<span class="{segment.tone} {segment.flaw}">{segment.text}</span
	>{/each}
