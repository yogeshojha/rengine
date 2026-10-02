<script lang="ts">
	import PanelSkeleton from '$lib/components/skeleton/panel-skeleton.svelte';
	import { whoisApi } from '$lib/api/whois';
	import { goto } from '$app/navigation';
	import { SvelteSet } from 'svelte/reactivity';
	import {
		type WhoisCorrelationResult,
		type WhoisRecordSummary,
		CORRELATION_REASON_LABELS,
		whoisLookupLabel
	} from '$lib/types/whois';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Empty from '$lib/components/ui/empty';
	import { Badge } from '$lib/components/ui/badge';
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

	function openTarget(targetId: string) {
		onOpenChange(false);
		goto(ROUTES.target(targetId));
	}

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
			error = e instanceof Error ? e.message : 'Lookup failed';
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
	<Dialog.Content
		class="w-[calc(100%-2rem)] max-w-lg max-h-[80vh] flex flex-col p-0 gap-0 overflow-hidden"
	>
		<div class="shrink-0">
			<Dialog.Header class="px-6 pt-6 pb-4">
				<div class="flex items-center gap-3">
					<div class="flex items-center justify-center h-10 w-10 rounded-xl bg-muted shrink-0">
						<meta.icon class="h-5 w-5 text-muted-foreground" />
					</div>
					<div class="min-w-0 flex-1">
						<Dialog.Title class="text-base font-semibold">
							Records sharing {meta.label.toLowerCase()}
						</Dialog.Title>
						<Dialog.Description class="text-sm text-muted-foreground font-mono truncate">
							{correlationValue}
						</Dialog.Description>
					</div>
				</div>
			</Dialog.Header>
		</div>

		<ScrollArea class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(80vh-6rem)]">
			<div class="px-6 pb-6">
				{#if isLoading}
					<PanelSkeleton rows={5} />
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
							<Empty.Title>No other records share this {meta.label.toLowerCase()}</Empty.Title>
						</Empty.Header>
					</Empty.Root>
				{:else}
					<div class="space-y-3">
						<div class="text-sm text-muted-foreground">
							<span class="font-medium text-foreground">{records.length}</span>
							{records.length === 1 ? 'record' : 'records'}
						</div>

						<div class="space-y-2">
							{#each records as record (record.id)}
								{#if record.target_id}
									{@const targetId = record.target_id}
									<div
										role="button"
										tabindex="0"
										onclick={() => openTarget(targetId)}
										onkeydown={(e) => {
											if (e.key === 'Enter' || e.key === ' ') {
												e.preventDefault();
												openTarget(targetId);
											}
										}}
										class="cursor-pointer rounded-lg border border-border/60 p-3.5 hover:border-border hover:bg-accent/50 transition-colors space-y-2"
									>
										{@render recordBody(record)}
									</div>
								{:else}
									<div class="rounded-lg border border-border/60 p-3.5 space-y-2">
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
