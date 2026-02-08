<script lang="ts">
	import { whoisApi } from '$lib/api/whois';
	import type { WhoisCorrelationResult, WhoisRecordSummary } from '$lib/types/whois';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Empty from '$lib/components/ui/empty';
	import { Badge } from '$lib/components/ui/badge';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { formatShortDate } from '$lib/utilities/dates';
	import {
		Loader,
		TriangleAlert,
		UserRound,
		Building,
		Server,
		Flag,
		Globe,
		Cable,
		SearchX
	} from 'lucide-svelte';

	interface Props {
		open: boolean;
		correlationType: string;
		correlationValue: string;
		onOpenChange: (open: boolean) => void;
	}

	let {
		open = $bindable(),
		correlationType,
		correlationValue,
		onOpenChange
	}: Props = $props();

	let results = $state<WhoisCorrelationResult[]>([]);
	let records = $state<WhoisRecordSummary[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	let headerEl = $state<HTMLDivElement | null>(null);
	let scrollHeight = $state(0);

	const TYPE_META: Record<string, { label: string; icon: typeof Globe; color: string }> = {
		registrant_name: {
			label: 'Registrant',
			icon: UserRound,
			color: 'text-violet-500'
		},
		registrant: {
			label: 'Registrant',
			icon: UserRound,
			color: 'text-violet-500'
		},
		registrar_name: {
			label: 'Registrar',
			icon: Building,
			color: 'text-blue-500'
		},
		registrar: {
			label: 'Registrar',
			icon: Building,
			color: 'text-blue-500'
		},
		nameserver: {
			label: 'Nameserver',
			icon: Server,
			color: 'text-cyan-500'
		},
		network_cidr: {
			label: 'Network',
			icon: Cable,
			color: 'text-emerald-500'
		},
		network: {
			label: 'Network',
			icon: Cable,
			color: 'text-emerald-500'
		},
		country: {
			label: 'Country',
			icon: Flag,
			color: 'text-amber-500'
		}
	};

	let meta = $derived(TYPE_META[correlationType] ?? { label: correlationType, icon: Globe, color: 'text-muted-foreground' });

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

	function measureScrollHeight() {
		if (!headerEl) return;
		requestAnimationFrame(() => {
			const dialogMaxH = Math.min(window.innerHeight * 0.8, window.innerHeight - 40);
			const headerH = headerEl?.offsetHeight ?? 0;
			const available = dialogMaxH - headerH;
			scrollHeight = Math.min(Math.max(available, 200), 500);
		});
	}

	$effect(() => {
		if (open && correlationType && correlationValue) {
			loadCorrelation();
		} else if (!open) {
			results = [];
			records = [];
			error = null;
			scrollHeight = 0;
		}
	});

	$effect(() => {
		if (open && headerEl) {
			measureScrollHeight();
		}
	});

	async function loadCorrelation() {
		isLoading = true;
		error = null;
		records = [];

		try {
			let data: WhoisCorrelationResult[];

			switch (correlationType) {
				case 'registrant':
				case 'registrant_name':
					data = await whoisApi.correlateByRegistrant(correlationValue);
					break;
				case 'registrar':
				case 'registrar_name':
					data = await whoisApi.correlateByRegistrar(correlationValue);
					break;
				case 'nameserver':
					data = await whoisApi.correlateByNameserver(correlationValue);
					break;
				case 'network':
				case 'network_cidr':
					data = await whoisApi.correlateByNetwork(correlationValue);
					break;
				case 'country':
					data = await whoisApi.correlateByCountry(correlationValue);
					break;
				default:
					data = [];
			}

			results = data;
			const seen = new Set<string>();
			const all: WhoisRecordSummary[] = [];
			for (const group of data) {
				for (const r of group.records) {
					if (!seen.has(r.id)) {
						seen.add(r.id);
						all.push(r);
					}
				}
			}
			records = all.sort((a, b) => a.query_value.localeCompare(b.query_value));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Lookup failed';
		} finally {
			isLoading = false;
		}
	}
</script>

<Dialog.Root bind:open {onOpenChange}>
	<Dialog.Content class="max-w-lg max-h-[80vh] flex flex-col p-0 gap-0 overflow-hidden">
		<div bind:this={headerEl} class="shrink-0">
			<Dialog.Header class="px-6 pt-6 pb-4">
				<div class="flex items-center gap-3">
					<div class="flex items-center justify-center h-10 w-10 rounded-xl bg-primary/10 shrink-0">
						<meta.icon class="h-5 w-5 {meta.color}" />
					</div>
					<div class="min-w-0 flex-1">
						<Dialog.Title class="text-base font-semibold">
							Targets sharing {meta.label.toLowerCase()}
						</Dialog.Title>
						<Dialog.Description class="text-sm text-muted-foreground font-mono truncate">
							{correlationValue}
						</Dialog.Description>
					</div>
				</div>
			</Dialog.Header>
		</div>

		{#if scrollHeight > 0}
			<ScrollArea style="height: {scrollHeight}px">
				<div class="px-6 pb-6">
					{#if isLoading}
						<Empty.Root>
							<Empty.Header>
								<Empty.Media variant="icon">
									<Loader class="animate-spin" />
								</Empty.Media>
								<Empty.Title>Searching targets…</Empty.Title>
							</Empty.Header>
						</Empty.Root>
					{:else if error}
						<Empty.Root>
							<Empty.Header>
								<Empty.Media variant="icon">
									<TriangleAlert />
								</Empty.Media>
								<Empty.Title>Lookup failed</Empty.Title>
								<Empty.Description>{error}</Empty.Description>
							</Empty.Header>
						</Empty.Root>
					{:else if records.length === 0}
						<Empty.Root>
							<Empty.Header>
								<Empty.Media variant="icon">
									<SearchX />
								</Empty.Media>
								<Empty.Title>No targets found</Empty.Title>
								<Empty.Description>
									No other targets share this {meta.label.toLowerCase()}.
								</Empty.Description>
							</Empty.Header>
						</Empty.Root>
					{:else}
						<div class="space-y-3">
							<div class="text-sm text-muted-foreground">
								<span class="font-medium text-foreground">{records.length}</span>
								{records.length === 1 ? 'target' : 'targets'} found
							</div>

							<div class="space-y-2">
								{#each records as record}
									<div class="rounded-lg border border-border/60 p-3.5 hover:border-border transition-colors space-y-2">
										<div class="flex items-center justify-between gap-3">
											<div class="min-w-0 flex-1">
												<div class="flex items-center gap-2">
													<span class="text-sm font-mono font-medium truncate">
														{record.query_value}
													</span>
													<Badge
														class="text-[10px] font-normal border shrink-0 {getLookupTypeBadgeColor(record.lookup_type)}"
													>
														{record.lookup_type}
													</Badge>
												</div>
												{#if record.name && record.name !== record.query_value}
													<p class="text-xs text-muted-foreground truncate mt-0.5">{record.name}</p>
												{/if}
											</div>
										</div>

										<div class="flex items-center gap-3 text-xs text-muted-foreground">
											{#if record.registrant_name}
												<div class="flex items-center gap-1 truncate">
													<UserRound class="h-3 w-3 shrink-0" />
													<span class="truncate">{record.registrant_name}</span>
												</div>
											{/if}
											{#if record.registrar_name}
												<div class="flex items-center gap-1 truncate">
													<Building class="h-3 w-3 shrink-0" />
													<span class="truncate">{record.registrar_name}</span>
												</div>
											{/if}
											{#if record.country}
												<div class="flex items-center gap-1">
													<Flag class="h-3 w-3 shrink-0" />
													<span>{record.country}</span>
												</div>
											{/if}
										</div>

										{#if record.registration_date || record.expiration_date}
											<div class="flex items-center gap-3 text-[11px] text-muted-foreground/70">
												{#if record.registration_date}
													<span>Registered {formatShortDate(record.registration_date)}</span>
												{/if}
												{#if record.expiration_date}
													<span>Expires {formatShortDate(record.expiration_date)}</span>
												{/if}
											</div>
										{/if}
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</ScrollArea>
		{/if}
	</Dialog.Content>
</Dialog.Root>
