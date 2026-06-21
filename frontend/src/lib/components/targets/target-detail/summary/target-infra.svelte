<script lang="ts">
	import type { Target } from '$lib/types/target';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import { buildTargetSummary, type InfraEntry } from './derive';
	import CopyButton from '$lib/components/copy-button.svelte';
	import * as ScrollArea from '$lib/components/ui/scroll-area/index.js';

	interface Props {
		target: Target;
		detail: TargetDetailRead | null;
	}

	let { target, detail }: Props = $props();

	const summary = $derived(buildTargetSummary(target, detail));

	type Group = { key: string; label: string; badge: string; entries: InfraEntry[] };
	const GROUP_META: Record<InfraEntry['kind'], { label: string; badge: string }> = {
		ipv4: { label: 'Addresses', badge: 'A' },
		ipv6: { label: 'Addresses', badge: 'AAAA' },
		ns: { label: 'Nameservers', badge: 'NS' },
		mx: { label: 'Mail exchangers', badge: 'MX' }
	};

	const groups = $derived.by<Group[]>(() => {
		const order: InfraEntry['kind'][] = ['ipv4', 'ipv6', 'ns', 'mx'];
		const out: Group[] = [];
		for (const kind of order) {
			const entries = summary.infra.filter((e) => e.kind === kind);
			if (entries.length) out.push({ key: kind, label: GROUP_META[kind].label, badge: GROUP_META[kind].badge, entries });
		}
		return out;
	});

	const total = $derived(summary.infra.length);
</script>

{#snippet rows()}
	<div class="divide-y divide-border/15">
		{#each groups as group (group.key)}
			{#each group.entries as entry (entry.value)}
				<div class="flex items-center gap-2 px-4 py-1.5 group/infra hover:bg-muted/40 transition-colors">
					<span class="text-[10px] font-mono font-semibold uppercase tracking-wide text-muted-foreground/60 w-10 shrink-0">
						{group.badge}
					</span>
					<code class="text-[11px] font-mono text-foreground/80 truncate flex-1">{entry.value}</code>
					{#if entry.note}
						<span class="text-[10px] font-mono text-muted-foreground/60 shrink-0">{entry.note}</span>
					{/if}
					<div class="opacity-100 sm:opacity-0 sm:group-hover/infra:opacity-100 sm:group-focus-within/infra:opacity-100 transition-opacity shrink-0">
						<CopyButton value={entry.value} />
					</div>
				</div>
			{/each}
		{/each}
	</div>
{/snippet}

{#if total > 0}
	<div class="rounded-lg border bg-card overflow-hidden">
		<div class="flex items-center justify-between px-4 py-2.5 border-b border-border/50">
			<h3 class="text-xs font-semibold tracking-tight text-foreground">Infrastructure</h3>
			<span class="text-[10px] font-mono tabular-nums text-muted-foreground/60">{total} assets</span>
		</div>

		{#if total > 10}
			<ScrollArea.Root class="h-[260px]" scrollbarYClasses="w-1.5">
				{@render rows()}
			</ScrollArea.Root>
		{:else}
			{@render rows()}
		{/if}
	</div>
{/if}
