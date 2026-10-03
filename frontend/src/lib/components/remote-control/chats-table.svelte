<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import MessageSquareIcon from '@lucide/svelte/icons/message-square';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import CapabilityLadder from './capability-ladder.svelte';
	import ChatDialog from './chat-dialog.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { CHAT_STATE_LABELS, ChatState } from '$lib/config/channels';
	import { chatUsable, type ChannelChat, type ChannelStatus } from '$lib/types/remote-control';
	import { CHAT_COL } from './columns';

	interface Props {
		status: ChannelStatus;
	}

	let { status }: Props = $props();

	let editing = $state<ChannelChat | null>(null);
	let pending = $state<{ chat: ChannelChat; action: 'revoke' | 'delete' } | null>(null);
	let confirming = $state(false);

	const chats = $derived(
		[...remoteControl.chats].sort((a, b) => {
			const ua = chatUsable(a) ? 0 : 1;
			const ub = chatUsable(b) ? 0 : 1;
			if (ua !== ub) return ua - ub;
			return (b.last_seen_at ?? b.created_at).localeCompare(a.last_seen_at ?? a.created_at);
		})
	);

	const unblocking = $derived(pending?.chat.state === ChatState.BLOCKED);

	async function run(chat: ChannelChat, action: 'revoke' | 'delete'): Promise<boolean> {
		if (action === 'revoke') return remoteControl.revokeChat(chat.id);
		if (chat.state === ChatState.BLOCKED) return remoteControl.unblockChat(chat.id);
		return remoteControl.deleteChat(chat.id);
	}

	async function confirm() {
		if (!pending) return;
		confirming = true;
		try {
			if (await run(pending.chat, pending.action)) pending = null;
		} finally {
			confirming = false;
		}
	}
</script>

{#if chats.length}
	<div class="@container/chats w-full" role="table" aria-label="Paired chats">
		<div
			class="flex items-center gap-4 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
			role="row"
		>
			<div class={CHAT_COL.chat}>Chat</div>
			<div class={CHAT_COL.account}>Account</div>
			<div class={CHAT_COL.project}>Project</div>
			<div class={CHAT_COL.capabilities}>Capabilities</div>
			<div class={CHAT_COL.last}>Last command</div>
			<div class={CHAT_COL.actions}></div>
		</div>
		{#each chats as chat (chat.id)}
			{@const usable = chatUsable(chat)}
			<div
				class="flex items-center gap-4 border-b border-border/60 px-4 py-2.5 last:border-b-0 {usable
					? ''
					: 'text-muted-foreground'}"
				role="row"
			>
				<div class={CHAT_COL.chat}>
					<div class="text-sm leading-5 font-medium wrap-anywhere">
						{chat.display || chat.external_id}
					</div>
					{#if !usable}
						<div class="text-2xs text-muted-foreground">{CHAT_STATE_LABELS[chat.state]}</div>
					{/if}
				</div>
				<div class={CHAT_COL.account}>
					<div class="text-sm leading-5 wrap-anywhere">{chat.username ?? 'No account'}</div>
					{#if usable && chat.username && !chat.totp_enabled}
						<div class="text-2xs text-warning">No authenticator</div>
					{/if}
				</div>
				<div class="{CHAT_COL.project} text-sm leading-5 wrap-anywhere">
					{chat.project_name ?? 'None'}
				</div>
				<div class={CHAT_COL.capabilities}>
					{#if usable}<CapabilityLadder {chat} />{/if}
				</div>
				<div class={CHAT_COL.last}>
					{#if chat.last_command && chat.last_seen_at}
						<div class="font-mono text-xs leading-5 wrap-anywhere">/{chat.last_command}</div>
						<div class="text-2xs text-muted-foreground">{relativeTime(chat.last_seen_at)}</div>
					{:else}
						<span class="text-sm leading-5 text-muted-foreground">Unused</span>
					{/if}
				</div>
				<div class={CHAT_COL.actions}>
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon"
									class="size-7"
									aria-label="{chat.display || chat.external_id} actions"
								>
									<EllipsisIcon class="size-4" />
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end">
							{#if usable}
								<DropdownMenu.Item onSelect={() => (editing = chat)}>Edit</DropdownMenu.Item>
								<DropdownMenu.Separator />
								<DropdownMenu.Item
									variant="destructive"
									onSelect={() => (pending = { chat, action: 'revoke' })}
								>
									Revoke
								</DropdownMenu.Item>
							{/if}
							<DropdownMenu.Item
								variant={chat.state === ChatState.BLOCKED ? 'default' : 'destructive'}
								onSelect={() => (pending = { chat, action: 'delete' })}
							>
								{chat.state === ChatState.BLOCKED ? 'Unblock' : 'Delete'}
							</DropdownMenu.Item>
						</DropdownMenu.Content>
					</DropdownMenu.Root>
				</div>
			</div>
		{/each}
	</div>
{:else}
	<div class="px-4 py-10">
		<EmptyState
			compact
			icon={MessageSquareIcon}
			title="No paired chats"
			description={status.bot ? `Message @${status.bot.username} to request pairing.` : undefined}
		/>
	</div>
{/if}

<ChatDialog
	{status}
	chat={editing}
	onOpenChange={(v) => {
		if (!v) editing = null;
	}}
/>

<ConfirmDialog
	open={pending !== null}
	title={pending?.action === 'revoke' ? 'Revoke chat' : unblocking ? 'Unblock chat' : 'Delete chat'}
	description={pending
		? pending.action === 'revoke'
			? `Chat ${pending.chat.display} loses access. Its next message starts pairing again.`
			: unblocking
				? `Chat ${pending.chat.display} can request pairing again.`
				: `Chat ${pending.chat.display} is removed. Its next message starts pairing again.`
		: ''}
	confirmLabel={pending?.action === 'revoke' ? 'Revoke' : unblocking ? 'Unblock' : 'Delete'}
	loadingLabel={pending?.action === 'revoke' ? 'Revoking' : unblocking ? 'Unblocking' : 'Deleting'}
	destructive={!unblocking}
	loading={confirming}
	onOpenChange={(v) => {
		if (!v) pending = null;
	}}
	onConfirm={confirm}
/>
