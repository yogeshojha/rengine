<script lang="ts">
	import type { Target } from '$lib/types/target';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import { buildTargetSummary, type InfraEntry } from './derive';
	import * as Card from '$lib/components/ui/card';
	import PanelHead from '$lib/components/panel-head.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import * as ScrollArea from '$lib/components/ui/scroll-area/index.js';

	interface Props {
		target: Target;
		detail: TargetDetailRead | null;
	}

	let { target, detail }: Props = $props();

	const summary = $derived(buildTargetSummary(target, detail));

	type Group = { key: string; badge: string; entries: InfraEntry[] };
	const BADGE: Record<InfraEntry['kind'], string> = {
		ipv4: 'A',
		ipv6: 'AAAA',
		ns: 'NS',
		mx: 'MX'
	};
	const SCROLL_AFTER = 10;

	const groups = $derived.by<Group[]>(() => {
		const order: InfraEntry['kind'][] = ['ipv4', 'ipv6', 'ns', 'mx'];
		return order
			.map((kind) => ({
				key: kind,
				badge: BADGE[kind],
				entries: summary.infra.filter((e) => e.kind === kind)
			}))
			.filter((g) => g.entries.length > 0);
	});

	const total = $derived(summary.infra.length);
</script>

{#snippet rows()}
	<ul class="divide-y">
		{#each groups as group (group.key)}
			{#each group.entries as entry (entry.value)}
				<li
					class="group/infra flex items-center gap-3 px-5 py-2 transition-colors hover:bg-muted/30"
				>
					<span
						class="w-10 shrink-0 font-mono text-xs font-medium tracking-wide text-muted-foreground uppercase"
					>
						{group.badge}
					</span>
					<code class="min-w-0 flex-1 truncate font-mono text-xs">{entry.value}</code>
					{#if entry.note}
						<span class="shrink-0 text-xs text-muted-foreground">{entry.note}</span>
					{/if}
					<span
						class="flex h-5 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover/infra:opacity-100 sm:group-focus-within/infra:opacity-100"
					>
						<CopyButton value={entry.value} />
					</span>
				</li>
			{/each}
		{/each}
	</ul>
{/snippet}

{#if total > 0}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Infrastructure" description="Records this target resolves through">
			<span class="tabular-nums">{total} {total === 1 ? 'record' : 'records'}</span>
		</PanelHead>
		{#if total > SCROLL_AFTER}
			<ScrollArea.Root class="h-[17rem]" scrollbarYClasses="w-1.5">
				{@render rows()}
			</ScrollArea.Root>
		{:else}
			{@render rows()}
		{/if}
	</Card.Root>
{/if}
