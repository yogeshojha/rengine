<script lang="ts">
	import { untrack } from 'svelte';
	import CompassIcon from '@lucide/svelte/icons/compass';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import XIcon from '@lucide/svelte/icons/x';
	import CheckIcon from '@lucide/svelte/icons/check';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
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

	let working = $state<string | null>(null);
	let added = $state<Map<string, TargetAdded>>(new Map());
	let error = $state<string | null>(null);
	let pending = $state<{ domain: string; action: 'add' | 'dismiss' } | null>(null);

	const rows = $derived(connectors.discovered);

	$effect(() => {
		const id = connector.id;
		untrack(() => void connectors.loadDiscovered(id, projectId));
	});

	async function reload() {
		await connectors.loadDiscovered(connector.id, projectId);
		await connectors.load(projectId, true);
	}

	async function add(domain: string) {
		working = domain;
		error = null;
		try {
			const result = await connectorsApi.addTarget(connector.id, projectId, domain);
			added = new Map([...added, [domain, result]]);
			await reload();
			const slug = targetsStore.filters?.projectSlug;
			if (slug) void targetsStore.fetchAll(slug, 1, true);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Target not added.';
		} finally {
			working = null;
		}
	}

	function confirm() {
		if (!pending) return;
		const { domain, action } = pending;
		pending = null;
		if (action === 'dismiss') void dismiss(domain);
		else void add(domain);
	}

	async function dismiss(domain: string) {
		working = domain;
		error = null;
		try {
			await connectorsApi.dismissDomain(connector.id, projectId, domain);
			await reload();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Domain not dismissed.';
		} finally {
			working = null;
		}
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	{#if error}
		<p class="text-destructive border-b px-5 py-2.5 text-xs">{error}</p>
	{/if}

	{#if rows.length === 0}
		<div class="px-4 py-10">
			<EmptyState icon={CompassIcon} title="No new domains" />
		</div>
	{:else}
		<div class="divide-y">
			{#each rows as row (row.domain)}
				<div class="flex flex-wrap items-start gap-4 px-5 py-4">
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
								disabled={working === row.domain}
								onclick={() => (pending = { domain: row.domain, action: 'dismiss' })}
							>
								<XIcon class="size-3.5" />
								Dismiss
							</Button>
							{#if !row.out_of_scope}
								<LoadingButton
									loading={working === row.domain}
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
</Card.Root>

<ConfirmDialog
	open={pending !== null}
	title={pending
		? pending.action === 'dismiss'
			? `Dismiss ${pending.domain}`
			: `Add ${pending.domain} as a target`
		: ''}
	confirmLabel={pending?.action === 'dismiss' ? 'Dismiss' : 'Add target'}
	onOpenChange={(v) => {
		if (!v) pending = null;
	}}
	onConfirm={confirm}
/>
