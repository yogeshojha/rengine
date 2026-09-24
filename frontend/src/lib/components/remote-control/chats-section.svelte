<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import MoreVerticalIcon from '@lucide/svelte/icons/more-vertical';
	import MessageSquareIcon from '@lucide/svelte/icons/message-square';
	import SectionHead from '$lib/components/section-head.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import CapabilityChips from '$lib/components/mcp/capability-chips.svelte';
	import ChatDialog from './chat-dialog.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { CHAT_STATE_LABELS, ChatState } from '$lib/config/channels';
	import { chatUsable, type ChannelChat, type ChannelStatus } from '$lib/types/remote-control';

	interface Props {
		status: ChannelStatus;
		canAdmin: boolean;
		onStart: () => void;
	}

	let { status, canAdmin, onStart }: Props = $props();

	const HEAD =
		'px-4 py-2 text-left text-2xs font-semibold tracking-wider text-muted-foreground uppercase whitespace-nowrap';

	let editing = $state<ChannelChat | null>(null);
	let pending = $state<{ chat: ChannelChat; action: 'revoke' | 'delete' } | null>(null);

	const chats = $derived(
		[...remoteControl.chats].sort((a, b) => {
			const ua = chatUsable(a) ? 0 : 1;
			const ub = chatUsable(b) ? 0 : 1;
			if (ua !== ub) return ua - ub;
			return (b.last_seen_at ?? b.created_at).localeCompare(a.last_seen_at ?? a.created_at);
		})
	);
	const launching = $derived(
		chats.filter((c) => chatUsable(c) && c.effective_capabilities.includes('launch')).length
	);

	async function confirm() {
		if (!pending) return;
		const { chat, action } = pending;
		pending = null;
		if (action === 'revoke') await remoteControl.revokeChat(chat.id);
		else await remoteControl.deleteChat(chat.id);
	}
</script>

<section class="flex flex-col gap-3 py-5">
	<SectionHead title="Paired chats" count={chats.length || null}>
		{#if launching}
			<span class="flex items-center gap-1.5 text-warning">
				<span class="size-1.5 rounded-full bg-warning" aria-hidden="true"></span>
				{launching} can launch scans
			</span>
		{/if}
	</SectionHead>

	{#if !status.enabled}
		<div
			class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-dashed px-4 py-3"
		>
			<span class="text-sm text-muted-foreground">Listener stopped</span>
			{#if canAdmin}
				<Button size="sm" onclick={onStart}>Start listener</Button>
			{/if}
		</div>
	{/if}

	{#if !canAdmin}
		<p class="text-sm text-muted-foreground">Paired chats are visible to administrators.</p>
	{:else if chats.length}
		<ScrollArea orientation="horizontal" class="rounded-md border">
			<table class="w-full min-w-[56rem] text-sm">
				<thead>
					<tr class="border-b bg-muted/40">
						<th class={HEAD}>Chat</th>
						<th class={HEAD}>Account</th>
						<th class={HEAD}>Project</th>
						<th class={HEAD}>Capabilities</th>
						<th class={HEAD}>Usage</th>
						<th class={HEAD}>State</th>
						<th class={HEAD}><span class="sr-only">Actions</span></th>
					</tr>
				</thead>
				<tbody>
					{#each chats as chat (chat.id)}
						{@const usable = chatUsable(chat)}
						<tr class="border-b last:border-b-0 {usable ? '' : 'text-muted-foreground'}">
							<td class="px-4 py-2.5">
								<div class="leading-5 font-medium">{chat.display || chat.external_id}</div>
								<div class="font-mono text-xs text-muted-foreground">{chat.external_id}</div>
							</td>
							<td class="px-4 py-2.5 whitespace-nowrap">
								{#if chat.username}
									<div class="leading-5">{chat.username}</div>
									<div class="text-xs text-muted-foreground">
										{chat.totp_enabled ? 'Authenticator enrolled' : 'No authenticator'}
									</div>
								{:else}
									<span class="text-muted-foreground">No account</span>
								{/if}
							</td>
							<td class="px-4 py-2.5 whitespace-nowrap">
								{chat.project_name ?? 'None selected'}
							</td>
							<td class="px-4 py-2.5">
								{#if usable && chat.effective_capabilities.length < chat.capabilities.length}
									<Hint
										text="Read only until {chat.username ?? 'the account'} enrols an authenticator."
									>
										{#snippet child(props)}
											<span {...props} class="inline-flex">
												<CapabilityChips
													granted={chat.effective_capabilities}
													ladder
													class="flex-nowrap"
												/>
											</span>
										{/snippet}
									</Hint>
								{:else}
									<CapabilityChips granted={chat.capabilities} ladder class="flex-nowrap" />
								{/if}
							</td>
							<td class="px-4 py-2.5 whitespace-nowrap">
								{#if chat.last_seen_at}
									<div class="leading-5">
										<span class="tabular-nums">{chat.calls.toLocaleString()} commands</span>
										<span class="text-muted-foreground"> · {relativeTime(chat.last_seen_at)}</span>
									</div>
									{#if chat.last_command}
										<div class="font-mono text-xs text-muted-foreground">/{chat.last_command}</div>
									{/if}
								{:else}
									<span class="text-muted-foreground">Unused</span>
								{/if}
							</td>
							<td class="px-4 py-2.5 whitespace-nowrap">
								{CHAT_STATE_LABELS[chat.state]}
							</td>
							<td class="w-12 px-2 py-2.5 text-right">
								<DropdownMenu.Root>
									<DropdownMenu.Trigger>
										{#snippet child({ props })}
											<Button {...props} variant="ghost" size="icon" class="size-7">
												<MoreVerticalIcon class="size-4" />
												<span class="sr-only">Chat actions</span>
											</Button>
										{/snippet}
									</DropdownMenu.Trigger>
									<DropdownMenu.Content align="end">
										{#if usable}
											<DropdownMenu.Item onSelect={() => (editing = chat)}>Edit</DropdownMenu.Item>
											<DropdownMenu.Item onSelect={() => (pending = { chat, action: 'revoke' })}>
												Revoke
											</DropdownMenu.Item>
										{/if}
										<DropdownMenu.Item
											variant="destructive"
											onSelect={() => (pending = { chat, action: 'delete' })}
										>
											{chat.state === ChatState.BLOCKED ? 'Unblock' : 'Delete'}
										</DropdownMenu.Item>
									</DropdownMenu.Content>
								</DropdownMenu.Root>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</ScrollArea>
	{:else}
		<EmptyState
			compact
			icon={MessageSquareIcon}
			title="No paired chats"
			description="A chat that messages the bot appears under pairing requests."
		/>
	{/if}
</section>

<ChatDialog
	{status}
	chat={editing}
	onOpenChange={(v) => {
		if (!v) editing = null;
	}}
/>

<ConfirmDialog
	open={pending !== null}
	title={pending?.action === 'revoke'
		? 'Revoke chat'
		: pending?.chat.state === ChatState.BLOCKED
			? 'Unblock chat'
			: 'Delete chat'}
	description={pending
		? pending.action === 'revoke'
			? `Chat ${pending.chat.display} loses access. Its next message starts pairing again.`
			: pending.chat.state === ChatState.BLOCKED
				? `Chat ${pending.chat.display} can request pairing again.`
				: `Chat ${pending.chat.display} is removed. Its next message starts pairing again.`
		: ''}
	confirmLabel={pending?.action === 'revoke'
		? 'Revoke'
		: pending?.chat.state === ChatState.BLOCKED
			? 'Unblock'
			: 'Delete'}
	destructive={pending?.chat.state !== ChatState.BLOCKED}
	onOpenChange={(v) => {
		if (!v) pending = null;
	}}
	onConfirm={confirm}
/>
