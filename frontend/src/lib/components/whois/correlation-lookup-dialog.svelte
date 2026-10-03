<script lang="ts">
	import PanelSkeleton from '$lib/components/skeleton/panel-skeleton.svelte';
	import { whoisApi } from '$lib/api/whois';
	import { SvelteSet } from 'svelte/reactivity';
	import {
		type WhoisCorrelationResult,
		type WhoisRecordSummary,
		CORRELATION_REASON_LABELS,
		whoisLookupLabel
	} from '$lib/types/whois';
	import * as Dialog from '$lib/components/ui/dialog';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { formatShortDate } from '$lib/utilities/dates';
	import { ROUTES } from '$lib/config/routes';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { IconComponent } from '$lib/config/icons';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import UserRound from '@lucide/svelte/icons/user-round';
	import Building from '@lucide/svelte/icons/building';
	import Server from '@lucide/svelte/icons/server';
	import Flag from '@lucide/svelte/icons/flag';
	import Globe from '@lucide/svelte/icons/globe';
	import Cable from '@lucide/svelte/icons/cable';
	import SearchX from '@lucide/svelte/icons/search-x';

	interface Props {
		open: boolean;
		correlationType: string;
		correlationValue: string;
		onOpenChange: (open: boolean) => void;
	}

	let { open = $bindable(), correlationType, correlationValue, onOpenChange }: Props = $props();

	let records = $state<WhoisRecordSummary[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	const TYPE_META: Record<string, { label: string; icon: IconComponent }> = {
		registrant_name: { label: CORRELATION_REASON_LABELS.registrant_name.short, icon: UserRound },
		registrar_name: { label: CORRELATION_REASON_LABELS.registrar_name.short, icon: Building },
		nameserver: { label: CORRELATION_REASON_LABELS.nameserver.short, icon: Server },
		network_cidr: { label: CORRELATION_REASON_LABELS.network_cidr.short, icon: Cable }
	};

	let meta = $derived(
		TYPE_META[correlationType] ?? {
			label: correlationType,
			icon: Globe
		}
	);

	$effect(() => {
		if (open && correlationType && correlationValue) {
			loadCorrelation();
		} else if (!open) {
			records = [];
			error = null;
		}
	});

	async function loadCorrelation() {
		isLoading = true;
		error = null;
		records = [];

		try {
			let data: WhoisCorrelationResult[];
			const projectId = projectsStore.activeProject?.id;

			if (!projectId) {
				data = [];
			} else {
				switch (correlationType) {
					case 'registrant_name':
						data = await whoisApi.correlateByRegistrant(correlationValue, projectId);
						break;
					case 'registrar_name':
						data = await whoisApi.correlateByRegistrar(correlationValue, projectId);
						break;
					case 'nameserver':
						data = await whoisApi.correlateByNameserver(correlationValue, projectId);
						break;
					case 'network_cidr':
						data = await whoisApi.correlateByNetwork(correlationValue, projectId);
						break;
					default:
						data = [];
				}
			}

			const seen = new SvelteSet<string>();
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
			error = e instanceof Error ? e.message : 'Records not loaded';
		} finally {
			isLoading = false;
		}
	}
</script>

{#snippet recordBody(record: WhoisRecordSummary)}
	<div class="flex items-center justify-between gap-3">
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
		<div class="flex items-center gap-3 text-2xs text-muted-foreground/70">
			{#if record.registration_date}
				<span>Registered {formatShortDate(record.registration_date)}</span>
			{/if}
			{#if record.expiration_date}
				<span>Expires {formatShortDate(record.expiration_date)}</span>
			{/if}
		</div>
	{/if}
{/snippet}

<Dialog.Root bind:open {onOpenChange}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg">
		<Dialog.Header class="border-b px-6 py-4 pr-12">
			<div class="flex items-center gap-3">
				<div
					class="flex size-10 shrink-0 items-center justify-center rounded-lg border bg-muted/40"
				>
					<meta.icon class="size-5 text-muted-foreground" />
				</div>
				<div class="flex min-w-0 flex-1 flex-col gap-1">
					<Dialog.Title>Records sharing {meta.label.toLowerCase()}</Dialog.Title>
					<Dialog.Description class="truncate font-mono">{correlationValue}</Dialog.Description>
				</div>
			</div>
		</Dialog.Header>

		<ScrollArea class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-5rem)]">
			<div class="px-6 py-5">
				{#if isLoading}
					<PanelSkeleton rows={5} />
				{:else if error}
					<EmptyState compact icon={TriangleAlert} title="Records not loaded" description={error}>
						<Button size="sm" variant="outline" onclick={() => loadCorrelation()}>Retry</Button>
					</EmptyState>
				{:else if records.length === 0}
					<EmptyState compact icon={SearchX} title="No other records" />
				{:else}
					<div class="space-y-3">
						<div class="text-sm text-muted-foreground">
							<span class="font-medium text-foreground tabular-nums">{records.length}</span>
							{records.length === 1 ? 'record' : 'records'}
						</div>

						<div class="space-y-2">
							{#each records as record (record.id)}
								{#if record.target_id}
									<a
										href={ROUTES.target(record.target_id)}
										onclick={() => onOpenChange(false)}
										class="block space-y-2 rounded-lg border border-border/60 p-3.5 transition-colors hover:border-border hover:bg-accent/50"
									>
										{@render recordBody(record)}
									</a>
								{:else}
									<div class="space-y-2 rounded-lg border border-border/60 p-3.5">
										{@render recordBody(record)}
									</div>
								{/if}
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</ScrollArea>
	</Dialog.Content>
</Dialog.Root>
