<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import * as Card from '$lib/components/ui/card';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import ConnectPanel from '$lib/components/remote-control/connect-panel.svelte';
	import BotHeader from '$lib/components/remote-control/bot-header.svelte';
	import ApprovalCard from '$lib/components/remote-control/approval-card.svelte';
	import ChatsTable from '$lib/components/remote-control/chats-table.svelte';
	import ActivityTable from '$lib/components/remote-control/activity-table.svelte';
	import CommandsList from '$lib/components/remote-control/commands-list.svelte';
	import SettingsSheet from '$lib/components/remote-control/settings-sheet.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { usersApi, type UserAccount } from '$lib/api/users';
	import { routeLabels } from '$lib/config/routes';
	import {
		CHANNEL_ORDER,
		CHANNEL_VIEW_LABELS,
		CHANNEL_VIEWS,
		type ChannelView,
		REMOTE_CONTROL_POLL_MS
	} from '$lib/config/channels';
	import type { PairingRequest } from '$lib/types/remote-control';

	const TICK_MS = 1000;
	const channel = CHANNEL_ORDER[0];

	const canAdmin = $derived(auth.user?.is_superuser ?? false);
	const views = $derived<readonly ChannelView[]>(
		canAdmin ? CHANNEL_VIEWS : CHANNEL_VIEWS.filter((v) => v !== 'chats')
	);
	const asked = page.url.searchParams.get('view') ?? '';
	let chosen = $state<ChannelView | null>(
		(CHANNEL_VIEWS as readonly string[]).includes(asked) ? (asked as ChannelView) : null
	);
	const view = $derived(chosen && views.includes(chosen) ? chosen : views[0]);

	let now = $state(Date.now());
	let settingsOpen = $state(false);
	let accounts = $state<UserAccount[]>([]);
	let blocking = $state<PairingRequest | null>(null);

	const status = $derived(remoteControl.status);
	const tabs = $derived(views.map((key) => ({ key, label: CHANNEL_VIEW_LABELS[key] })));
	const counts = $derived<Record<string, number | null>>({
		chats: remoteControl.chats.length || null,
		activity: remoteControl.calls.length || null,
		commands: remoteControl.commands.length || null
	});

	$effect(() => {
		const admin = canAdmin;
		untrack(() => {
			void remoteControl.fetch(channel, true);
			void remoteControl.loadCalls(true);
			if (admin) {
				void remoteControl.loadAdmin(true);
				void usersApi
					.list()
					.then((rows) => (accounts = rows.filter((r) => r.is_active)))
					.catch(() => (accounts = []));
			}
		});
	});

	$effect(() => {
		void projectsStore.fetchProjects();
	});

	$effect(() => {
		if (!browser) return;
		const admin = canAdmin;
		const poll = () => {
			if (document.hidden) return;
			void remoteControl.refreshStatus(true);
			void remoteControl.loadCalls(true);
			if (admin) void remoteControl.loadAdmin(true);
		};
		const id = setInterval(poll, REMOTE_CONTROL_POLL_MS);
		const tick = setInterval(() => (now = Date.now()), TICK_MS);
		return () => {
			clearInterval(id);
			clearInterval(tick);
		};
	});

	$effect(() => {
		const current = view;
		if (!browser) return;
		const params = untrack(() => new URLSearchParams(page.url.searchParams));
		if (current === views[0]) params.delete('view');
		else params.set('view', current);
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {
			// ignore
		}
	});

	async function block() {
		if (!blocking) return;
		const code = blocking.code;
		blocking = null;
		await remoteControl.block(code);
	}
</script>

<svelte:head><title>{routeLabels['remote-control']} · reNgine</title></svelte:head>

<div class="flex flex-col gap-4 p-4 md:p-6">
	<h1 class="sr-only">{routeLabels['remote-control']}</h1>

	{#if !status}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<div class="flex items-center gap-4 border-b px-4 py-4">
				<Skeleton class="size-10 rounded-lg" />
				<div class="flex flex-col gap-2">
					<Skeleton class="h-4 w-40" />
					<Skeleton class="h-3 w-24" />
				</div>
			</div>
			<div class="flex flex-col gap-3 p-4">
				<Skeleton class="h-8 w-full" />
				<Skeleton class="h-8 w-full" />
				<Skeleton class="h-8 w-full" />
			</div>
		</Card.Root>
	{:else}
		<Card.Root class="gap-0 overflow-hidden py-0">
			{#if !status.configured}
				<ConnectPanel {channel} label={status.label} {canAdmin} />
			{:else}
				<BotHeader {status} {canAdmin} onSettings={() => (settingsOpen = true)} />

				{#if canAdmin}
					{#each remoteControl.pending as request (request.code)}
						<ApprovalCard {request} {status} {accounts} {now} onBlock={(r) => (blocking = r)} />
					{/each}
				{/if}

				<div class="border-b px-2">
					<CountTabs {tabs} value={view} {counts} onChange={(k) => (chosen = k as ChannelView)} />
				</div>
				{#if view === 'chats'}
					<ChatsTable {status} />
				{:else if view === 'activity'}
					<ActivityTable calls={remoteControl.calls} commands={remoteControl.commands} />
				{:else}
					<CommandsList commands={remoteControl.commands} />
				{/if}
			{/if}
		</Card.Root>

		{#if canAdmin && status.configured}
			<SettingsSheet {status} bind:open={settingsOpen} />
		{/if}
	{/if}
</div>

<ConfirmDialog
	open={blocking !== null}
	title="Block chat"
	description={blocking ? `Chat ${blocking.display} is blocked. Its messages are ignored.` : ''}
	confirmLabel="Block"
	destructive
	onOpenChange={(v) => {
		if (!v) blocking = null;
	}}
	onConfirm={block}
/>
