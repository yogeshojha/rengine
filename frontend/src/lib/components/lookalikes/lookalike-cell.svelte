<script lang="ts">
	import Cell from '$lib/components/cell.svelte';
	import { Button } from '$lib/components/ui/button';
	import LookalikeName from './lookalike-name.svelte';
	import LookalikeSheet from './lookalike-sheet.svelte';
	import { SEVERITY_CHIP } from '$lib/config/vulnerabilities';
	import { LookalikeState, VERDICTS, VERDICT_BY_KEY, Verdict } from '$lib/config/lookalikes';
	import type { LookalikeSummary } from '$lib/types/lookalike';

	interface Props {
		summary: LookalikeSummary;
		projectId: string;
		onChanged?: () => void;
		class?: string;
	}

	let { summary, projectId, onChanged, class: className = '' }: Props = $props();

	const TOP = 4;
	let open = $state(false);
	let verdict = $state<string | null>(null);

	let rows = $derived(summary.rows.filter((r) => r.state === LookalikeState.OPEN));
	let lines = $derived(
		VERDICTS.map((v) => ({ ...v, count: rows.filter((r) => r.verdict === v.key).length })).filter(
			(v) => v.count > 0
		)
	);
	let peak = $derived(Math.max(1, ...lines.map((l) => l.count)));
	let top = $derived(rows.filter((r) => r.verdict !== Verdict.LINKED).slice(0, TOP));

	function show(key: string | null) {
		verdict = key;
		open = true;
	}
</script>

<Cell
	id="lookalikes"
	title="Lookalike domains"
	description="Registered typo, homoglyph and TLD variants"
	class={className}
>
	{#snippet tools()}
		<Button variant="ghost" size="sm" class="h-6 px-2 text-xs" onclick={() => show(null)}>
			Review
		</Button>
	{/snippet}
	{#if lines.length}
		<ul class="flex flex-col gap-1.5">
			{#each lines as l (l.key)}
				<li>
					<button
						type="button"
						class="grid w-full grid-cols-[7.5rem_1fr_2.75rem] items-center gap-2.5 rounded-sm text-left text-xs hover:text-foreground"
						onclick={() => show(l.key)}
					>
						<span class="truncate text-muted-foreground">{l.label}</span>
						<span class="h-1.5 overflow-hidden rounded-full bg-muted">
							<span
								class="block h-full rounded-full {SEVERITY_CHIP[l.severity].edge}"
								style="width:{(l.count / peak) * 100}%"
							></span>
						</span>
						<span class="text-right font-medium tabular-nums">{l.count.toLocaleString()}</span>
					</button>
				</li>
			{/each}
		</ul>
		{#if top.length}
			<ul class="flex flex-col gap-1 border-t pt-2.5">
				{#each top as r (r.domain)}
					{@const spec = VERDICT_BY_KEY[r.verdict]}
					<li class="flex items-start gap-2 text-xs">
						<span class="flex h-4 shrink-0 items-center">
							<span
								class="size-1.5 rounded-full {spec
									? SEVERITY_CHIP[spec.severity].edge
									: 'bg-muted'}"
							></span>
						</span>
						<LookalikeName display={r.display} domain={r.display} apex={r.apex} class="min-w-0" />
					</li>
				{/each}
			</ul>
		{/if}
	{:else}
		<span class="text-sm text-muted-foreground">No open lookalikes</span>
	{/if}
	{#snippet footer()}
		<span>
			{#if summary.permutations != null}{summary.permutations.toLocaleString()} permutations ·
			{/if}{summary.registered.toLocaleString()} registered
		</span>
		<span class="font-mono">{summary.apex}</span>
	{/snippet}
</Cell>

<LookalikeSheet
	{open}
	onOpenChange={(o) => (open = o)}
	bind:verdict
	{summary}
	{projectId}
	{onChanged}
/>
