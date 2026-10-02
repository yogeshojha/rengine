<script lang="ts">
	import PanelSkeleton from '$lib/components/skeleton/panel-skeleton.svelte';
	import {
		type WhoisCorrelationResult,
		type WhoisRecordSummary,
		CORRELATION_REASON_LABELS,
		whoisLookupLabel
	} from '$lib/types/whois';
	import { Badge } from '$lib/components/ui/badge';
	import * as Empty from '$lib/components/ui/empty';
	import Hint from '$lib/components/hint.svelte';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Link2 from '@lucide/svelte/icons/link-2';
	import GitBranch from '@lucide/svelte/icons/git-branch';
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

	const REASON_LABELS = CORRELATION_REASON_LABELS as Record<
		string,
		{ full: string; match: string; short: string }
	>;
	const reasonLabel = (t: string) => REASON_LABELS[t];

	function buildMatchSummary(reasons: CorrelationReason[]): string {
		const labels = reasons.map((r) => reasonLabel(r.type)?.match ?? r.type);
		return `Matching ${new Intl.ListFormat('en-GB', { type: 'conjunction' }).format(labels)}`;
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
</script>

{#if isLoading}
	<PanelSkeleton rows={5} />
{:else if error}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<SearchX />
			</Empty.Media>
			<Empty.Title>Related records not loaded</Empty.Title>
			<Empty.Description>{error}</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else if relatedTargets.length === 0}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<GitBranch />
			</Empty.Media>
			<Empty.Title>No related records</Empty.Title>
		</Empty.Header>
	</Empty.Root>
{:else}
	<div class="space-y-4 py-1">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2 text-sm text-muted-foreground">
				<Link2 class="h-4 w-4" />
				<span>
					<span class="font-medium text-foreground">{relatedTargets.length}</span>
					related {relatedTargets.length === 1 ? 'record' : 'records'}
				</span>
			</div>
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
									class="text-2xs font-normal shrink-0 text-muted-foreground border-border/60"
								>
									{whoisLookupLabel(record.lookup_type)}
								</Badge>
							</div>
							{#if record.name && record.name !== record.query_value}
								<p class="text-xs text-muted-foreground truncate mt-0.5">{record.name}</p>
							{/if}
						</div>
					</div>

					<p class="text-xs text-muted-foreground">{buildMatchSummary(reasons)}</p>

					<div class="flex flex-wrap gap-1.5">
						{#each reasons as reason (reason.type + reason.value)}
							{#each expandReasonValues(reason) as { type, value } (type + value)}
								<Hint text="Records sharing this {reasonLabel(type)?.match ?? type}">
									{#snippet child(props)}
										<button
											{...props}
											onclick={() => handleBadgeClick(type, value)}
											class="cursor-pointer"
										>
											<span
												class="inline-flex items-center text-2xs border border-border/60 rounded-md overflow-hidden hover:ring-1 hover:ring-ring/30 transition-shadow"
											>
												<span class="px-2 py-1 font-medium bg-muted/60 text-foreground/70">
													{reasonLabel(type)?.full ?? type}
												</span>
												<span
													class="px-2 py-1 font-mono border-l border-border/60 text-foreground truncate max-w-[200px]"
												>
													{value}
												</span>
											</span>
										</button>
									{/snippet}
								</Hint>
							{/each}
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}
