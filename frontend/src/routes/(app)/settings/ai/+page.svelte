<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import CpuIcon from '@lucide/svelte/icons/cpu';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import AiProvidersPanel from '$lib/components/settings/ai-providers-panel.svelte';
	import AiUsageSheet from '$lib/components/settings/ai-usage-sheet.svelte';
	import SettingRow from '$lib/components/settings/setting-row.svelte';
	import { ai } from '$lib/stores/ai.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { formatCost } from '$lib/config/ai';
	import { AI_USAGE_PANEL, PANEL_PARAM, routeLabels } from '$lib/config/routes';
	import { formatShortDate } from '$lib/utilities/dates';
	import { pageTitle } from '$lib/utilities/page-title';

	let usageOpen = $state(page.url.searchParams.get(PANEL_PARAM) === AI_USAGE_PANEL);
	let settled = $state(ai.hasFetched);

	const status = $derived(ai.status);
	const catalog = $derived(ai.catalog);
	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const usage = $derived(status?.usage ?? null);
	const spend = $derived.by(() => {
		if (!usage?.calls) return 'No calls';
		const calls = `${usage.calls.toLocaleString()} ${usage.calls === 1 ? 'call' : 'calls'}`;
		return usage.cost_usd === null ? calls : `${formatCost(usage.cost_usd)} · ${calls}`;
	});

	function load() {
		void ai.fetch(true).finally(() => (settled = true));
	}

	$effect(() => {
		untrack(load);
	});

	$effect(() => {
		if (usageOpen) return;
		const params = untrack(() => new URLSearchParams(page.url.searchParams));
		if (params.get(PANEL_PARAM) !== AI_USAGE_PANEL) return;
		params.delete(PANEL_PARAM);
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {}
	});

	async function setFeature(key: string, label: string, value: boolean) {
		if (await ai.save({ features: { [key]: value } })) {
			toast.success(`${label} ${value ? 'enabled' : 'disabled'}`);
		}
	}
</script>

<svelte:head><title>{pageTitle(routeLabels.ai)}</title></svelte:head>

{#if !status && (!settled || ai.isLoading)}
	<Card.Root class="gap-3 p-5">
		<Skeleton class="h-4 w-24" />
		<Skeleton class="h-9 w-full" />
		<Skeleton class="h-9 w-full" />
	</Card.Root>
{:else if !status}
	<EmptyState compact icon={CpuIcon} title="AI settings not loaded">
		<Button variant="outline" size="sm" onclick={() => load()}>
			<RotateCwIcon class="size-3.5" />
			Retry
		</Button>
	</EmptyState>
{:else}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<AiProvidersPanel />

		<div id="ai-features" class="scroll-mt-20"></div>
		<PanelHead title="Features" class="border-t" />
		{#each catalog?.features ?? [] as feature, i (feature.key)}
			<SettingRow
				label={feature.label}
				help={feature.help}
				for="ai-feature-{feature.key}"
				class={i === 0 ? 'border-t-0' : ''}
			>
				<Switch
					id="ai-feature-{feature.key}"
					checked={status.features[feature.key] ?? feature.default}
					disabled={!isAdmin || ai.isSaving}
					onCheckedChange={(v) => setFeature(feature.key, feature.label, v)}
				/>
			</SettingRow>
		{/each}

		<div class="flex flex-wrap items-center gap-x-3 gap-y-1 border-t px-5 py-3">
			<span class="text-sm tabular-nums">{spend}</span>
			{#if usage?.since}
				<span class="text-xs text-muted-foreground tabular-nums">
					since {formatShortDate(usage.since)}
				</span>
			{/if}
			<Button variant="ghost" size="sm" class="ml-auto" onclick={() => (usageOpen = true)}>
				Usage
				<ChevronRightIcon class="size-4" />
			</Button>
		</div>
		{#if !isAdmin}
			<div class="border-t px-5 py-2.5 text-xs text-muted-foreground">
				Editable by administrators.
			</div>
		{/if}
	</Card.Root>
{/if}

<AiUsageSheet bind:open={usageOpen} />
