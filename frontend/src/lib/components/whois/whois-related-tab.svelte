<script lang="ts">
	import type { WhoisCorrelationResult, WhoisRecordSummary } from '$lib/types/whois';
	import { Badge } from '$lib/components/ui/badge';
	import * as Empty from '$lib/components/ui/empty';
	import { Loader, SearchX, Link2, ShieldAlert, GitBranch } from 'lucide-svelte';

	interface Props {
		correlations: WhoisCorrelationResult[];
		isLoading: boolean;
		error: string | null;
		currentRecordId?: string;
	}

	let { correlations, isLoading, error, currentRecordId }: Props = $props();

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
		network_cidr: 'Network Block',
		country: 'Country',
		country_code: 'Country'
	};

	const REASON_MATCH_LABELS: Record<string, string> = {
		registrant: 'registrant name',
		registrant_name: 'registrant name',
		registrar: 'registrar',
		registrar_name: 'registrar',
		nameserver: 'nameserver',
		network: 'network block',
		network_cidr: 'network block',
		country: 'country',
		country_code: 'country'
	};

	const REASON_COLORS: Record<
		string,
		{ bg: string; label: string; value: string; border: string }
	> = {
		registrant: {
			bg: 'bg-violet-500/10',
			label: 'text-violet-600 dark:text-violet-400',
			value: 'bg-violet-500/5 text-violet-700 dark:text-violet-300',
			border: 'border-violet-500/20'
		},
		registrant_name: {
			bg: 'bg-violet-500/10',
			label: 'text-violet-600 dark:text-violet-400',
			value: 'bg-violet-500/5 text-violet-700 dark:text-violet-300',
			border: 'border-violet-500/20'
		},
		registrar: {
			bg: 'bg-blue-500/10',
			label: 'text-blue-600 dark:text-blue-400',
			value: 'bg-blue-500/5 text-blue-700 dark:text-blue-300',
			border: 'border-blue-500/20'
		},
		registrar_name: {
			bg: 'bg-blue-500/10',
			label: 'text-blue-600 dark:text-blue-400',
			value: 'bg-blue-500/5 text-blue-700 dark:text-blue-300',
			border: 'border-blue-500/20'
		},
		nameserver: {
			bg: 'bg-cyan-500/10',
			label: 'text-cyan-600 dark:text-cyan-400',
			value: 'bg-cyan-500/5 text-cyan-700 dark:text-cyan-300',
			border: 'border-cyan-500/20'
		},
		network: {
			bg: 'bg-emerald-500/10',
			label: 'text-emerald-600 dark:text-emerald-400',
			value: 'bg-emerald-500/5 text-emerald-700 dark:text-emerald-300',
			border: 'border-emerald-500/20'
		},
		network_cidr: {
			bg: 'bg-emerald-500/10',
			label: 'text-emerald-600 dark:text-emerald-400',
			value: 'bg-emerald-500/5 text-emerald-700 dark:text-emerald-300',
			border: 'border-emerald-500/20'
		},
		country: {
			bg: 'bg-amber-500/10',
			label: 'text-amber-600 dark:text-amber-400',
			value: 'bg-amber-500/5 text-amber-700 dark:text-amber-300',
			border: 'border-amber-500/20'
		},
		country_code: {
			bg: 'bg-amber-500/10',
			label: 'text-amber-600 dark:text-amber-400',
			value: 'bg-amber-500/5 text-amber-700 dark:text-amber-300',
			border: 'border-amber-500/20'
		}
	};

	const DEFAULT_REASON_COLORS = {
		bg: 'bg-muted',
		label: 'text-muted-foreground',
		value: 'bg-muted/50 text-foreground/70',
		border: 'border-border'
	};

	function getReasonColors(type: string) {
		return REASON_COLORS[type] ?? DEFAULT_REASON_COLORS;
	}

	function getLookupTypeBadgeColor(type: string): string {
		switch (type) {
			case 'DOMAIN':
				return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
			case 'IP':
				return 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20';
			case 'ASN':
				return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20';
			default:
				return 'bg-muted text-muted-foreground border-border';
		}
	}

	function buildMatchSummary(reasons: CorrelationReason[]): string {
		const labels = reasons.map((r) => REASON_MATCH_LABELS[r.type] ?? r.type);
		if (labels.length === 1) return `Matching ${labels[0]}`;
		if (labels.length === 2) return `Matching ${labels[0]} and ${labels[1]}`;
		const last = labels.pop();
		return `Matching ${labels.join(', ')}, and ${last}`;
	}

	let relatedTargets = $derived.by(() => {
		const map = new Map<string, RelatedTarget>();

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

		<!-- Target cards -->
		<div class="space-y-2">
			{#each relatedTargets as { record, reasons }}
				<div
					class="rounded-lg border border-border/60 p-4 space-y-3 hover:border-border transition-colors"
				>
					<!-- Target identity -->
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0 flex-1">
							<div class="flex items-center gap-2">
								<span class="text-sm font-mono font-medium truncate">
									{record.query_value}
								</span>
								<Badge
									class="text-[10px] font-normal border shrink-0 {getLookupTypeBadgeColor(
										record.lookup_type
									)}"
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
								class="text-[10px] shrink-0 gap-1 border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-500/5"
							>
								<ShieldAlert class="h-3 w-3" />
								Strong
							</Badge>
						{/if}
					</div>

					<!-- Match summary -->
					<p class="text-xs text-muted-foreground">{buildMatchSummary(reasons)}</p>

					<!-- Reason why it was related in the form of badge label | value label slighly dark-->
					<div class="flex flex-wrap gap-1.5">
						{#each reasons as reason}
							{#if getReasonColors(reason.type)}
								{@const colors = getReasonColors(reason.type)}
								<span
									class="inline-flex items-center text-[11px] border rounded-md overflow-hidden {colors.border}"
								>
									<span class="px-2 py-1 font-medium {colors.bg} {colors.label}">
										{REASON_LABELS[reason.type] ?? reason.type}
									</span>
									<span
										class="px-2 py-1 font-mono border-l {colors.value} {colors.border} break-all"
									>
										{reason.value}
									</span>
								</span>
							{/if}
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}
