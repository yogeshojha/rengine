<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import BookOpenIcon from '@lucide/svelte/icons/book-open';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import PageHeader from '$lib/components/page-header.svelte';
	import ReferenceOperation from '$lib/components/access-keys/reference-operation.svelte';
	import { accessKeysApi } from '$lib/api/access-keys';
	import { aboutApi } from '$lib/api/about';
	import { PROFILE_TAB_LABELS, ROUTES, routeLabels } from '$lib/config/routes';
	import { pageTitle } from '$lib/utilities/page-title';
	import { operationKey } from '$lib/utilities/access-keys';
	import type { ReferenceGroup } from '$lib/types/access-key';

	const GROUP_PARAM = 'group';

	let groups = $state<ReferenceGroup[]>([]);
	let version = $state<string | null>(null);
	let loading = $state(true);
	let loadError = $state<string | null>(null);

	const origin = $derived(page.url.origin);
	const shown = $derived(
		groups.find((g) => g.name === page.url.searchParams.get(GROUP_PARAM)) ?? groups[0] ?? null
	);

	async function load() {
		loading = true;
		loadError = null;
		try {
			groups = (await accessKeysApi.reference()).filter((g) => g.operations.length > 0);
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'API reference not loaded';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		void load();
		aboutApi
			.get()
			.then((about) => (version = about.version))
			.catch(() => (version = null));
	});

	function pick(name: string) {
		const url = new URL(page.url);
		url.searchParams.set(GROUP_PARAM, name);
		void goto(`${url.pathname}${url.search}`, {
			replaceState: true,
			noScroll: true,
			keepFocus: true
		});
	}
</script>

<svelte:head><title>{pageTitle(routeLabels['api-reference'])}</title></svelte:head>

<div class="flex w-full max-w-5xl flex-col gap-6">
	<PageHeader title={routeLabels['api-reference']} description="Endpoints an access key calls">
		{#snippet titleAside()}
			{#if version}
				<Badge variant="outline" class="font-mono">{version}</Badge>
			{/if}
		{/snippet}
		{#snippet actions()}
			<Button variant="outline" size="sm" href={ROUTES.profileTab('access-keys')}>
				{PROFILE_TAB_LABELS['access-keys']}
			</Button>
		{/snippet}
	</PageHeader>

	{#if loading}
		<div class="grid gap-6 md:grid-cols-[12rem_minmax(0,1fr)]">
			<div class="flex flex-col gap-2">
				{#each { length: 6 } as _, i (i)}
					<Skeleton class="h-7 w-full" />
				{/each}
			</div>
			<Card.Root class="gap-0 py-0">
				{#each { length: 4 } as _, i (i)}
					<div class="border-b border-border/60 px-4 py-3 last:border-b-0">
						<Skeleton class="h-5 w-2/3" />
					</div>
				{/each}
			</Card.Root>
		</div>
	{:else if loadError}
		<EmptyState
			compact
			icon={TriangleAlertIcon}
			title="API reference not loaded"
			description={loadError}
		>
			<Button variant="outline" size="sm" onclick={load}>
				<RotateCwIcon class="size-3.5" />
				Retry
			</Button>
		</EmptyState>
	{:else if !shown}
		<EmptyState compact icon={BookOpenIcon} title="No endpoints listed" />
	{:else}
		<div class="grid gap-6 md:grid-cols-[12rem_minmax(0,1fr)]">
			<nav
				class="flex flex-wrap gap-1 md:sticky md:top-4 md:flex-col md:self-start"
				aria-label="Groups"
			>
				{#each groups as group (group.name)}
					<button
						type="button"
						class="flex items-center justify-between gap-3 rounded-md px-2.5 py-1.5 text-sm transition-colors hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:outline-none {group ===
						shown
							? 'bg-muted font-medium text-foreground'
							: 'text-muted-foreground'}"
						aria-current={group === shown ? 'page' : undefined}
						onclick={() => pick(group.name)}
					>
						<span>{group.name}</span>
						<span class="text-xs tabular-nums text-muted-foreground">{group.operations.length}</span
						>
					</button>
				{/each}
			</nav>

			<Card.Root class="min-w-0 gap-0 overflow-hidden py-0">
				{#key shown.name}
					{#each shown.operations as operation (operationKey(operation))}
						<ReferenceOperation {operation} {origin} />
					{/each}
				{/key}
			</Card.Root>
		</div>
	{/if}
</div>
