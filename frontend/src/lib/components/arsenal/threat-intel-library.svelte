<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Flame from '@lucide/svelte/icons/flame';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import * as Card from '$lib/components/ui/card';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Switch } from '$lib/components/ui/switch';
	import Hint from '$lib/components/hint.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import FeedCard from '$lib/components/threat-intel/feed-card.svelte';
	import { threatIntelApi } from '$lib/api/threat-intel';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import type { ThreatIntelStatus } from '$lib/types/threat-intel';

	const POLL_MS = 4000;

	let status = $state<ThreatIntelStatus | null>(null);
	let loading = $state(true);
	let syncing = $state(false);
	let fetchedProjectId = $state<string | null>(null);
	let togglingAuto = $state(false);

	let projectId = $derived(projectsStore.activeProject?.id ?? null);

	let feeds = $derived(status?.feeds ?? []);

	let autoSync = $derived(status?.auto_sync ?? true);

	async function load(id: string | null) {
		try {
			status = await threatIntelApi.status(id ?? undefined);
			fetchedProjectId = id;
		} catch {
			status = null;
		} finally {
			loading = false;
		}
	}

	async function toggleAuto(enabled: boolean) {
		togglingAuto = true;
		try {
			status = await threatIntelApi.setAutoSync(enabled, fetchedProjectId ?? undefined);
			toast.success(enabled ? 'Nightly download on' : 'Nightly download off');
		} catch {
			toast.error('Download setting not saved');
		} finally {
			togglingAuto = false;
		}
	}

	async function sync() {
		syncing = true;
		try {
			const res = await threatIntelApi.sync();
			if (res.queued) {
				toast.success('Refresh started');
				setTimeout(() => load(fetchedProjectId), 2500);
			} else {
				toast.error(res.detail ?? 'Refresh not started');
			}
		} catch {
			toast.error('Refresh not started');
		} finally {
			syncing = false;
		}
	}

	$effect(() => {
		const id = projectId;
		if (id === fetchedProjectId && status) return;
		untrack(() => void load(id));
	});

	$effect(() => {
		if (!status?.syncing) return;
		const handle = setInterval(() => untrack(() => load(fetchedProjectId)), POLL_MS);
		return () => clearInterval(handle);
	});
</script>

{#if loading}
	<div class="grid gap-4 sm:grid-cols-2">
		<Skeleton class="h-56" />
		<Skeleton class="h-56" />
	</div>
{:else if !status}
	<EmptyState
		icon={Flame}
		title="Exploitation intelligence unavailable"
		description="The API did not respond. Check that the api service is running."
	/>
{:else}
	<div class="flex flex-col gap-6">
		<!-- feeds -->
		<Card.Root class="gap-0 py-0">
			<PanelHead
				title="Exploitation feeds"
				description={status.auto_sync
					? 'Downloaded nightly. No API key required.'
					: 'Automatic download is off.'}
			>
				{#if status.last_applied_at}
					<span>Last applied {relativeTime(status.last_applied_at)}</span>
				{/if}
				<Hint
					text={status.auto_sync
						? 'EPSS and the KEV catalog are downloaded once a day'
						: 'No scheduled download'}
				>
					{#snippet child(props)}
						<label {...props} class="flex cursor-pointer items-center gap-2">
							<Switch
								checked={autoSync}
								disabled={togglingAuto}
								onCheckedChange={toggleAuto}
								aria-label="Download feeds automatically"
							/>
							<span class="whitespace-nowrap">Nightly download</span>
						</label>
					{/snippet}
				</Hint>
				<LoadingButton
					loading={syncing || status.syncing}
					loadingLabel="Refreshing"
					variant="outline"
					size="sm"
					onclick={sync}
				>
					<RefreshCw class="mr-1.5 size-3.5" />
					Refresh now
				</LoadingButton>
			</PanelHead>
			<div class="grid sm:grid-cols-2 sm:divide-x">
				{#each feeds as feed (feed.kind)}
					<div class="border-b last:border-b-0 sm:border-b-0">
						<FeedCard {feed} />
					</div>
				{/each}
			</div>
		</Card.Root>

		<!-- the provider -->
		<Card.Root class="gap-0 py-0">
			<PanelHead
				title="vulnx"
				description="ProjectDiscovery vulnerability index. Fetched per CVE and cached."
			>
				<span class="tabular-nums">{status.provider_cached} CVEs cached</span>
			</PanelHead>
			<div class="px-5 py-4 text-xs leading-relaxed text-muted-foreground">
				<p>
					Adds exploit references, template availability, exposed host counts and HackerOne reports.
					Without an API key: 10 requests per minute.
					<a class="underline hover:text-foreground" href={ROUTES.settings('api-keys')}>API keys</a>
				</p>
			</div>
		</Card.Root>
	</div>
{/if}
