<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { EvidenceField, type EvidenceFieldValue } from '$lib/config/ask';
	import { cn } from '$lib/utils.js';

	interface Props {
		field: EvidenceFieldValue;
		lines: number[];
		text: string | null;
		mark: number;
		onOpen?: () => void;
		capped?: boolean;
	}

	let { field, lines, text, mark, onOpen, capped = false }: Props = $props();

	const CONTEXT = 1;

	interface Row {
		n: number;
		text: string;
		hit: boolean;
	}

	let rows = $derived.by(() => {
		if (!text || !lines.length) return [] as (Row | null)[];
		const all = text.split('\n');
		const wanted = [...new Set(lines)].sort((a, b) => a - b);
		const out: (Row | null)[] = [];
		let last = 0;
		for (const n of wanted) {
			const lo = Math.max(1, n - CONTEXT);
			const hi = Math.min(all.length, n + CONTEXT);
			if (last && lo > last + 1) out.push(null);
			for (let i = Math.max(lo, last + 1); i <= hi; i++) {
				out.push({ n: i, text: all[i - 1] ?? '', hit: wanted.includes(i) });
			}
			last = Math.max(last, hi);
		}
		return out;
	});

	let label = $derived(field === EvidenceField.REQUEST ? 'Request' : 'Response');
	let range = $derived(
		lines.length === 1 ? `line ${lines[0]}` : `lines ${Math.min(...lines)} to ${Math.max(...lines)}`
	);
</script>

<div class="overflow-hidden rounded-md border bg-card">
	<div
		class="flex h-7 items-center gap-2 border-b bg-muted/30 px-2.5 text-2xs text-muted-foreground"
	>
		<span
			class="inline-flex size-3.5 items-center justify-center rounded-sm bg-primary font-mono text-2xs font-semibold text-primary-foreground"
			>{mark}</span
		>
		{label} · {range}
		<span class="flex-1"></span>
		{#if onOpen}
			<Button variant="link" size="sm" class="h-auto p-0 text-2xs" onclick={onOpen}
				>Open Evidence</Button
			>
		{/if}
	</div>
	{#if rows.length && capped}
		<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-40">
			{@render body()}
		</ScrollArea>
	{:else if rows.length}
		{@render body()}
	{:else}
		<div class="px-2.5 py-2 text-2xs text-muted-foreground">
			{text ? 'Lines not found in the stored evidence.' : `${label} not stored.`}
		</div>
	{/if}
</div>

{#snippet body()}
	<div class="py-1 font-mono text-2xs leading-5">
		{#each rows as row, i (row ? row.n : `gap-${i}`)}
			{#if row}
				<div
					class={cn(
						'grid grid-cols-[2.25rem_minmax(0,1fr)] gap-2 px-2.5 whitespace-pre-wrap wrap-anywhere',
						row.hit && 'bg-primary/10 shadow-[inset_3px_0_0_var(--primary)]'
					)}
				>
					<span class="text-right text-muted-foreground tabular-nums">{row.n}</span>
					<span class={row.hit ? 'text-foreground' : 'text-muted-foreground'}>{row.text}</span>
				</div>
			{:else}
				<div class="px-2.5 text-muted-foreground">···</div>
			{/if}
		{/each}
	</div>
{/snippet}
