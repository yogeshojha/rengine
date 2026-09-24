<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import PlayIcon from '@lucide/svelte/icons/play';
	import SquareIcon from '@lucide/svelte/icons/square';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import ChannelPanel from '$lib/components/remote-control/channel-panel.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import {
		REMOTE_CONTROL_TABS,
		ROUTES,
		routeLabels,
		type RemoteControlTab
	} from '$lib/config/routes';
	import {
		CHANNEL_LABELS,
		CHANNEL_META,
		CHANNEL_ORDER,
		CHANNEL_VIEWS,
		type ChannelView,
		LISTENER_STATE_DOT,
		LISTENER_STATE_LABELS,
		REMOTE_CONTROL_POLL_MS
	} from '$lib/config/channels';
	import { listenerState } from '$lib/types/remote-control';
	import { uptime } from '$lib/utilities/dates';

	const DEFAULT_TAB: RemoteControlTab = REMOTE_CONTROL_TABS[0];
	const validTabs = new Set<string>(REMOTE_CONTROL_TABS);
	const TICK_MS = 1000;

	const initialTab = page.url.searchParams.get('tab') ?? DEFAULT_TAB;
	let activeTab = $state<RemoteControlTab>(
		validTabs.has(initialTab) ? (initialTab as RemoteControlTab) : DEFAULT_TAB
	);
	let confirmStop = $state(false);
	let view = $state<ChannelView>(
		(CHANNEL_VIEWS as readonly string[]).includes(page.url.searchParams.get('view') ?? '')
			? (page.url.searchParams.get('view') as ChannelView)
			: CHANNEL_VIEWS[0]
	);
	let now = $state(Date.now());

	const channel = $derived(activeTab);
	const meta = $derived(CHANNEL_META[channel]);
	const status = $derived(remoteControl.status);
	const listener = $derived(listenerState(status));
	const canAdmin = $derived(auth.user?.is_superuser ?? false);
	const activeChats = $derived(status?.chats_active ?? 0);

	$effect(() => {
		const kind = channel;
		untrack(() => {
			void remoteControl.fetch(kind, true);
			void remoteControl.loadCalls(true);
			if (canAdmin) void remoteControl.loadAdmin(true);
		});
	});

	$effect(() => {
		void projectsStore.fetchProjects();
	});

	$effect(() => {
		if (!browser) return;
		const poll = () => {
			if (document.hidden) return;
			void remoteControl.refreshStatus(true);
			void remoteControl.loadCalls(true);
			if (canAdmin) void remoteControl.loadAdmin(true);
		};
		const id = setInterval(poll, REMOTE_CONTROL_POLL_MS);
		const tick = setInterval(() => (now = Date.now()), TICK_MS);
		return () => {
			clearInterval(id);
			clearInterval(tick);
		};
	});

	$effect(() => {
		const tab = activeTab;
		const section = view;
		if (!browser) return;
		const params = untrack(() => new URLSearchParams(page.url.searchParams));
		if (tab === DEFAULT_TAB) params.delete('tab');
		else params.set('tab', tab);
		if (section === CHANNEL_VIEWS[0]) params.delete('view');
		else params.set('view', section);
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {
			// ignore
		}
	});

	async function start() {
		await remoteControl.setRunning(true);
	}

	async function stop() {
		confirmStop = false;
		await remoteControl.setRunning(false);
	}

	function requestStop() {
		if (activeChats) confirmStop = true;
		else void stop();
	}
</script>

<svelte:head><title>{routeLabels['remote-control']} · reNgine</title></svelte:head>

<div class="space-y-6 p-4 md:p-6">
	<header class="flex flex-wrap items-start justify-between gap-4">
		<div class="min-w-0">
			<h1 class="text-xl font-semibold">{routeLabels['remote-control']}</h1>
			<p class="mt-1 max-w-2xl text-sm text-muted-foreground">
				Chat channels that operate this instance
			</p>
		</div>
		{#if status}
			<div class="flex flex-wrap items-center gap-2">
				<Hint
					text={listener === 'unreachable'
						? 'The channels service is not reporting. Check that it is running.'
						: listener === 'faulted'
							? (status.listener.last_error ?? `${CHANNEL_LABELS[channel]} refused the connection.`)
							: ''}
				>
					{#snippet child(props)}
						<span
							{...props}
							class="inline-flex h-8 items-center gap-2 rounded-md border px-3 text-sm {listener ===
							'listening'
								? ''
								: 'text-muted-foreground'}"
						>
							<span class="size-2 rounded-full {LISTENER_STATE_DOT[listener]}" aria-hidden="true"
							></span>
							{LISTENER_STATE_LABELS[listener]}
							{#if listener === 'listening' && status.started_at}
								<span class="text-xs text-muted-foreground">{uptime(status.started_at)}</span>
							{/if}
						</span>
					{/snippet}
				</Hint>
				{#if canAdmin}
					{#if status.enabled}
						<Button
							variant="outline"
							size="sm"
							disabled={remoteControl.isSaving}
							onclick={requestStop}
							class="text-destructive hover:text-destructive"
						>
							<SquareIcon class="size-4" />
							Stop listener
						</Button>
					{:else}
						<Hint text={status.configured ? '' : `Add a ${meta.apiKeyLabel} first.`}>
							{#snippet child(props)}
								<span {...props} class="inline-flex">
									<LoadingButton
										size="sm"
										loading={remoteControl.isSaving}
										disabled={!status.configured}
										onclick={start}
									>
										<PlayIcon class="size-4" />
										Start listener
									</LoadingButton>
								</span>
							{/snippet}
						</Hint>
					{/if}
					<Button
						size="sm"
						variant={status.configured ? 'outline' : 'default'}
						href={ROUTES.settings('api-keys')}
					>
						<KeyRoundIcon class="size-4" />
						API key
					</Button>
				{/if}
			</div>
		{/if}
	</header>

	<Tabs.Root
		value={activeTab}
		onValueChange={(v) => {
			if (v) activeTab = v as RemoteControlTab;
		}}
	>
		<Tabs.List class="w-full sm:w-fit">
			{#each CHANNEL_ORDER as kind (kind)}
				<Tabs.Trigger value={kind} class="gap-1.5">
					{CHANNEL_LABELS[kind]}
					{#if status?.channel === kind && status.pending_total}
						<span class="text-2xs text-warning tabular-nums">{status.pending_total}</span>
					{/if}
				</Tabs.Trigger>
			{/each}
		</Tabs.List>

		{#each CHANNEL_ORDER as kind (kind)}
			<Tabs.Content value={kind} class="mt-6">
				{#if status && status.channel === kind}
					<ChannelPanel
						channel={kind}
						{status}
						{canAdmin}
						{now}
						{view}
						onStart={start}
						onView={(v) => (view = v)}
					/>
				{:else}
					<div class="grid gap-x-8 gap-y-6 lg:grid-cols-[minmax(0,1fr)_18.5rem]">
						<div class="flex flex-col gap-3">
							<Skeleton class="h-4 w-40" />
							<Skeleton class="h-16 w-full" />
							<Skeleton class="h-40 w-full" />
						</div>
						<Skeleton class="h-64 w-full" />
					</div>
				{/if}
			</Tabs.Content>
		{/each}
	</Tabs.Root>
</div>

<ConfirmDialog
	bind:open={confirmStop}
	title="Stop listener"
	description="{activeChats} paired chat{activeChats === 1
		? ' receives'
		: 's receive'} no replies while the listener is stopped."
	confirmLabel="Stop listener"
	destructive
	loading={remoteControl.isSaving}
	onOpenChange={(v) => (confirmStop = v)}
	onConfirm={stop}
/>
