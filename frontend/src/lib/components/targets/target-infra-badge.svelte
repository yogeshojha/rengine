<script lang="ts">
	import { whoisApi } from '$lib/api/whois';
	import type { WhoisCorrelationResult } from '$lib/types/whois';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import Share2 from '@lucide/svelte/icons/share-2';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';

	interface Props {
		targetId: string;
		whoisRecordId: string | null;
		onClick?: () => void;
	}

	let { targetId, whoisRecordId, onClick }: Props = $props();

	const cache = new SvelteMap<
		string,
		{ total: number; breakdown: { label: string; count: number }[] }
	>();

	const TYPE_LABELS: Record<string, string> = {
		registrant_name: 'Registrant',
		registrar_name: 'Registrar',
		network_cidr: 'Network',
		nameserver: 'Nameserver'
	};

	let total = $state(0);
	let breakdown = $state<{ label: string; count: number }[]>([]);
	let loaded = $state(false);

	$effect(() => {
		void targetId;
		void whoisRecordId;
		fetchCorrelations();
	});

	async function fetchCorrelations() {
		loaded = false;
		total = 0;
		breakdown = [];
		if (!whoisRecordId) return;

		const cached = cache.get(targetId);
		if (cached) {
			total = cached.total;
			breakdown = cached.breakdown;
			loaded = true;
			return;
		}

		try {
			const groups = await whoisApi.getTargetCorrelations(targetId);
			const { t, b } = summarize(groups);
			total = t;
			breakdown = b;
			loaded = true;
			cache.set(targetId, { total: t, breakdown: b });
		} catch {
			//
		}
	}

	function summarize(groups: WhoisCorrelationResult[]) {
		const ids = new SvelteSet<string>();
		const b: { label: string; count: number }[] = [];
		for (const group of groups) {
			for (const r of group.records) ids.add(r.id);
			if (group.count > 0) {
				b.push({
					label: TYPE_LABELS[group.correlation_type] ?? group.correlation_type,
					count: group.count
				});
			}
		}
		return { t: ids.size, b };
	}

	function handleClick(e: MouseEvent) {
		e.stopPropagation();
		onClick?.();
	}
</script>

{#if loaded && total > 0}
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				<button
					{...props}
					type="button"
					class="inline-flex items-center gap-1 text-[11px] text-chart-1 hover:text-foreground transition-colors cursor-pointer"
					onclick={handleClick}
				>
					<Share2 class="h-3 w-3" />
					<span class="font-medium">{total}</span>
					<span class="hidden sm:inline">shared</span>
				</button>
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content side="bottom" align="start">
			<div class="space-y-1">
				<p class="font-medium">Shares infrastructure with {total} target{total === 1 ? '' : 's'}</p>
				{#each breakdown as b (b.label)}
					<p class="text-xs text-muted-foreground">{b.label}: {b.count}</p>
				{/each}
			</div>
		</Tooltip.Content>
	</Tooltip.Root>
{/if}
