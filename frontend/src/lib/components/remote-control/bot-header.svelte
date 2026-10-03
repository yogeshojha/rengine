<script lang="ts">
	import PlayIcon from '@lucide/svelte/icons/play';
	import SquareIcon from '@lucide/svelte/icons/square';
	import SettingsIcon from '@lucide/svelte/icons/settings';
	import { Button } from '$lib/components/ui/button/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { CHANNEL_META, LISTENER_STATE_DOT, LISTENER_STATE_LABELS } from '$lib/config/channels';
	import { listenerState, type ChannelStatus } from '$lib/types/remote-control';
	import { uptime } from '$lib/utilities/dates';
	import { getInitials } from '$lib/utilities/strings';
	import { externalHref } from '$lib/utilities/links';

	interface Props {
		status: ChannelStatus;
		canAdmin: boolean;
		onSettings: () => void;
	}

	let { status, canAdmin, onSettings }: Props = $props();

	let confirmStop = $state(false);

	const meta = $derived(CHANNEL_META[status.channel]);
	const listener = $derived(listenerState(status));
	const name = $derived(status.bot?.name || status.label);
	const initials = $derived(getInitials(name));
	const problem = $derived(
		listener === 'unreachable'
			? 'The channels service is not reporting. Check that it is running.'
			: listener === 'faulted'
				? (status.listener.last_error ?? `${status.label} refused the connection.`)
				: null
	);

	async function stop() {
		confirmStop = false;
		await remoteControl.setRunning(false);
	}
</script>

<div class="flex flex-wrap items-center gap-x-4 gap-y-3 border-b px-4 py-4">
	<div
		class="relative grid size-10 shrink-0 place-items-center rounded-lg border bg-muted font-mono text-sm font-semibold"
		aria-hidden="true"
	>
		{initials}
		<span
			class="absolute -right-1 -bottom-1 size-3 rounded-full border-2 border-card {LISTENER_STATE_DOT[
				listener
			]}"
		></span>
	</div>

	<div class="min-w-0 grow basis-56">
		<div class="flex flex-wrap items-baseline gap-x-2">
			<h2 class="text-base font-semibold">{name}</h2>
			{#if status.bot}
				<a
					href={externalHref(meta.chatUrl(status.bot.username))}
					target="_blank"
					rel="noopener noreferrer"
					class="font-mono text-xs text-primary hover:text-primary/80">@{status.bot.username}</a
				>
			{/if}
		</div>
		<div class="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
			<span class={listener === 'listening' ? 'text-foreground' : ''}>
				{LISTENER_STATE_LABELS[listener]}
			</span>
			{#if listener === 'listening' && status.started_at}
				<span>· {uptime(status.started_at)}</span>
			{/if}
			{#if problem}
				<span class="text-destructive">· {problem}</span>
			{/if}
		</div>
	</div>

	{#if canAdmin}
		<div class="flex flex-wrap items-center gap-2">
			<Button variant="outline" size="sm" onclick={onSettings}>
				<SettingsIcon class="size-4" />
				Settings
			</Button>
			{#if status.enabled}
				<Button
					variant="outline"
					size="sm"
					class="text-destructive hover:text-destructive"
					disabled={remoteControl.isSaving}
					onclick={() =>
						status.chats_active ? (confirmStop = true) : remoteControl.setRunning(false)}
				>
					<SquareIcon class="size-4" />
					Stop listener
				</Button>
			{:else}
				<LoadingButton
					size="sm"
					loading={remoteControl.isSaving}
					onclick={() => remoteControl.setRunning(true)}
				>
					<PlayIcon class="size-4" />
					Start listener
				</LoadingButton>
			{/if}
		</div>
	{/if}
</div>

<ConfirmDialog
	bind:open={confirmStop}
	title="Stop listener"
	description="{status.chats_active} paired chat{status.chats_active === 1
		? ' receives'
		: 's receive'} no replies while the listener is stopped."
	confirmLabel="Stop listener"
	destructive
	loading={remoteControl.isSaving}
	onOpenChange={(v) => (confirmStop = v)}
	onConfirm={stop}
/>
