<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import CompassIcon from '@lucide/svelte/icons/compass';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import XIcon from '@lucide/svelte/icons/x';
	import CheckIcon from '@lucide/svelte/icons/check';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { connectors } from '$lib/stores/connectors.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import type { Connector, TargetAdded } from '$lib/types/connector';

	let { connector, projectId }: { connector: Connector; projectId: string } = $props();

	type Pending = { domain: string; action: 'add' | 'dismiss' };

	let working = $state<Pending | null>(null);
	let added = $state<Map<string, TargetAdded>>(new Map());
	let pending = $state<Pending | null>(null);
	let loadedFor = $state<string | null>(null);

	const connectorId = $derived(connector.id);
	const rows = $derived(connectors.discovered);

	$effect(() => {
		const id = connectorId;
		untrack(() => {
			void connectors.loadDiscovered(id, projectId).then(() => (loadedFor = id));
		});
	});

	async function reload() {
		await connectors.loadDiscovered(connector.id, projectId);
		await connectors.load(projectId, true);
	}

	function retry() {
		const id = connectorId;
		loadedFor = null;
		void connectors.loadDiscovered(id, projectId).then(() => (loadedFor = id));
	}

	async function add(domain: string) {
		working = { domain, action: 'add' };
		try {
			const result = await connectorsApi.addTarget(connector.id, projectId, domain);
			added = new Map([...added, [domain, result]]);
			pending = null;
			await reload();
			const slug = targetsStore.filters?.projectSlug;
			if (slug) void targetsStore.fetchAll(slug, 1, true);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Target not added');
		} finally {
			working = null;
		}
	}

	function confirm() {
		if (!pending) return;
		const { domain, action } = pending;
		if (action === 'dismiss') void dismiss(domain);
		else void add(domain);
	}

	async function dismiss(domain: string) {
		working = { domain, action: 'dismiss' };
		try {
			await connectorsApi.dismissDomain(connector.id, projectId, domain);
			pending = null;
			await reload();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Domain not dismissed');
		} finally {
			working = null;
		}
	}
</script>

{#if rows.length === 0 && loadedFor !== connectorId}
	<div class="flex flex-col gap-2 p-4">
		{#each Array(4) as _, i (i)}
			<Skeleton class="h-16 w-full" />
		{/each}
	</div>
{:else if connectors.discoveredError && rows.length === 0}
	<EmptyState
		icon={TriangleAlertIcon}
		title="Domains not loaded"
		description={connectors.discoveredError}
		class="rounded-none border-0 bg-transparent py-16"
	>
		<Button variant="outline" size="sm" onclick={retry}>Retry</Button>
	</EmptyState>
{:else if rows.length === 0}
	<EmptyState
		icon={CompassIcon}
		title="No new domains"
		class="rounded-none border-0 bg-transparent py-16"
	/>
{:else}
	<div class="divide-y">
		{#each rows as row (row.domain)}
			<div class="flex flex-wrap items-start gap-4 px-4 py-4">
				<div class="min-w-0 flex-1 space-y-1">
					<div class="flex flex-wrap items-baseline gap-2">
						<span class="font-mono text-sm">{row.domain}</span>
						{#if row.out_of_scope}
							<span class="text-destructive flex items-center gap-1 text-2xs font-medium">
								<TriangleAlertIcon class="size-3" />
								Out of scope for {row.program}
							</span>
						{/if}
						<Hint text={row.reason_detail}>
							{#snippet child(props)}
								<span {...props} class="text-muted-foreground text-2xs">{row.reason_label}</span>
							{/snippet}
						</Hint>
					</div>
					<p class="text-muted-foreground truncate font-mono text-xs">
						{row.hostnames.join(', ')}
					</p>
					<p class="text-muted-foreground/70 text-2xs tabular-nums">
						{plural(row.hostname_count, 'host')} · {plural(row.requests, 'request')} · first seen
						{relativeTime(row.first_seen_at)}
					</p>
				</div>
				<div class="flex shrink-0 items-center gap-2">
					{#if added.has(row.domain)}
						{@const result = added.get(row.domain)!}
						<div class="flex items-center gap-2">
							<span class="text-success flex items-center gap-1 text-xs">
								<CheckIcon class="size-3.5" />
								Added{result.attached ? ` · ${result.attached} attached` : ''}
							</span>
						</div>
					{:else}
						<Button
							variant="ghost"
							size="sm"
							disabled={working?.domain === row.domain}
							onclick={() => (pending = { domain: row.domain, action: 'dismiss' })}
						>
							<XIcon class="size-3.5" />
							Dismiss
						</Button>
						{#if !row.out_of_scope}
							<LoadingButton
								loading={working?.domain === row.domain && working.action === 'add'}
								loadingLabel="Adding"
								disabled={working?.domain === row.domain}
								size="sm"
								onclick={() => (pending = { domain: row.domain, action: 'add' })}
							>
								<PlusIcon class="size-3.5" />
								Add as target
							</LoadingButton>
						{/if}
					{/if}
				</div>
			</div>
		{/each}
	</div>
{/if}

<ConfirmDialog
	open={pending !== null}
	title={pending
		? pending.action === 'dismiss'
			? `Dismiss ${pending.domain}`
			: `Add ${pending.domain} as a target`
		: ''}
	confirmLabel={pending?.action === 'dismiss' ? 'Dismiss' : 'Add target'}
	loadingLabel={pending?.action === 'dismiss' ? 'Dismissing' : 'Adding'}
	loading={working !== null}
	onOpenChange={(v) => {
		if (!v) pending = null;
	}}
	onConfirm={confirm}
/>
