<script lang="ts">
	import type { WhoisCorrelationResult, WhoisRecordSummary } from '$lib/types/whois';
	import { Badge } from '$lib/components/ui/badge';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Empty from '$lib/components/ui/empty';
	import { Loader, SearchX, Link2, ShieldAlert, GitBranch } from 'lucide-svelte';
	import { SvelteMap } from 'svelte/reactivity';

	interface Props {
		correlations: WhoisCorrelationResult[];
		isLoading: boolean;
		error: string | null;
		currentRecordId?: string;
		onCorrelationClick?: (type: string, value: string) => void;
	}

	let { correlations, isLoading, error, currentRecordId, onCorrelationClick }: Props = $props();

	interface CorrelationReason {
		type: string;
		value: string;
	}

	interface RelatedTarget {
		record: WhoisRecordSummary;
		reasons: CorrelationReason[];
	}

	const REASON_LABELS: Record<string, string> = {
		registrant: 'Registrant Name',
		registrant_name: 'Registrant Name',
		registrar: 'Registrar',
		registrar_name: 'Registrar',
		nameserver: 'Nameserver',
		network: 'Network Block',
		network_cidr: 'Network Block'
	};

	const REASON_MATCH_LABELS: Record<string, string> = {
		registrant: 'registrant name',
		registrant_name: 'registrant name',
		registrar: 'registrar',
		registrar_name: 'registrar',
		nameserver: 'nameserver',
		network: 'network block',
		network_cidr: 'network block'
	};

	function buildMatchSummary(reasons: CorrelationReason[]): string {
		const labels = reasons.map((r) => REASON_MATCH_LABELS[r.type] ?? r.type);
		if (labels.length === 1) return `Matching ${labels[0]}`;
		if (labels.length === 2) return `Matching ${labels[0]} and ${labels[1]}`;
		const last = labels.pop();
		return `Matching ${labels.join(', ')}, and ${last}`;
	}

	function expandReasonValues(reason: CorrelationReason): { type: string; value: string }[] {
		if (reason.type === 'nameserver' && reason.value.includes(',')) {
			return reason.value
				.split(',')
				.map((v) => v.trim())
				.filter(Boolean)
				.map((v) => ({ type: reason.type, value: v }));
		}
		return [{ type: reason.type, value: reason.value }];
	}

	function handleBadgeClick(type: string, value: string) {
		if (onCorrelationClick) {
			onCorrelationClick(type, value);
		}
	}

	let relatedTargets = $derived.by(() => {
		const map = new SvelteMap<string, RelatedTarget>();

		for (const group of correlations) {
			for (const record of group.records) {
				if (record.id === currentRecordId) continue;

				if (!map.has(record.id)) {
					map.set(record.id, { record, reasons: [] });
				}
				map.get(record.id)!.reasons.push({
					type: group.correlation_type,
					value: group.correlation_value
				});
			}
		}

		return [...map.values()].sort((a, b) => {
			if (b.reasons.length !== a.reasons.length) return b.reasons.length - a.reasons.length;
			return a.record.query_value.localeCompare(b.record.query_value);
		});
	});

	let strongMatchCount = $derived(relatedTargets.filter((t) => t.reasons.length >= 3).length);
</script>

{#if isLoading}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<Loader class="animate-spin" />
			</Empty.Media>
			<Empty.Title>Correlating infrastructure…</Empty.Title>
			<Empty.Description>
				Searching for related targets across your attack surface.
			</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else if error}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<SearchX />
			</Empty.Media>
			<Empty.Title>Correlation lookup failed</Empty.Title>
			<Empty.Description>{error}</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else if relatedTargets.length === 0}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<GitBranch />
			</Empty.Media>
			<Empty.Title>No related targets found</Empty.Title>
			<Empty.Description>
				Correlations surface automatically as your attack surface grows. Shared registrants,
				nameservers, networks, and registrars are tracked across all targets.
			</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else}
	<div class="space-y-4 py-1">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2 text-sm text-muted-foreground">
				<Link2 class="h-4 w-4" />
				<span>
					<span class="font-medium text-foreground">{relatedTargets.length}</span>
					related {relatedTargets.length === 1 ? 'target' : 'targets'} found
				</span>
			</div>
			{#if strongMatchCount > 0}
				<Badge variant="outline" class="gap-1.5 text-xs font-normal">
					<ShieldAlert class="h-3 w-3" />
					{strongMatchCount} strong {strongMatchCount === 1 ? 'match' : 'matches'}
				</Badge>
			{/if}
		</div>

		<div class="space-y-2">
			{#each relatedTargets as { record, reasons } (record.id)}
				<div
					class="rounded-lg border border-border/60 p-4 space-y-3 hover:border-border transition-colors"
				>
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0 flex-1">
							<div class="flex items-center gap-2">
								<span class="text-sm font-mono font-medium truncate">
									{record.query_value}
								</span>
								<Badge
									variant="outline"
									class="text-[10px] font-normal shrink-0 text-muted-foreground border-border/60"
								>
									{record.lookup_type}
								</Badge>
							</div>
							{#if record.name && record.name !== record.query_value}
								<p class="text-xs text-muted-foreground truncate mt-0.5">{record.name}</p>
							{/if}
						</div>
						{#if reasons.length >= 3}
							<Badge
								variant="outline"
								class="text-[10px] shrink-0 gap-1 border-amber-500/30 text-amber-600 dark:text-amber-500 bg-amber-500/10"
							>
								<ShieldAlert class="h-3 w-3" />
								Strong
							</Badge>
						{/if}
					</div>

					<p class="text-xs text-muted-foreground">{buildMatchSummary(reasons)}</p>

					<div class="flex flex-wrap gap-1.5">
						{#each reasons as reason (reason.type + reason.value)}
							{#each expandReasonValues(reason) as { type, value } (type + value)}
								<Tooltip.Root>
									<Tooltip.Trigger>
										{#snippet child({ props })}
											<button
												{...props}
												onclick={() => handleBadgeClick(type, value)}
												class="cursor-pointer"
											>
												<span
													class="inline-flex items-center text-[11px] border border-border/60 rounded-md overflow-hidden hover:ring-1 hover:ring-chart-1/30 transition-shadow"
												>
													<span class="px-2 py-1 font-medium bg-muted/60 text-foreground/70">
														{REASON_LABELS[type] ?? type}
													</span>
													<span
														class="px-2 py-1 font-mono border-l border-border/60 text-foreground truncate max-w-[200px]"
													>
														{value}
													</span>
												</span>
											</button>
										{/snippet}
									</Tooltip.Trigger>
									<Tooltip.Content>
										<p>Find all targets sharing this {REASON_MATCH_LABELS[type] ?? type}</p>
									</Tooltip.Content>
								</Tooltip.Root>
							{/each}
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}
