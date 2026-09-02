<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import Check from '@lucide/svelte/icons/check';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import { relativeTime } from '$lib/utilities/dates.js';
	import { getSeverityIcon, getTypeIcon } from '$lib/utilities/notification-icons';
	import { NOTIFICATION_TYPE_LABELS, type Notification } from '$lib/types/notification';
	import { cn } from '$lib/utils.js';

	interface Props {
		notification: Notification;
		variant?: 'compact' | 'full';
		onSelect: (id: number) => void;
		onAction: (id: number, event: Event) => void;
		onDelete: (id: number, event: Event) => void;
		onMarkRead: (id: number, event: Event) => void;
	}

	let {
		notification,
		variant = 'compact',
		onSelect,
		onAction,
		onDelete,
		onMarkRead
	}: Props = $props();

	const full = $derived(variant === 'full');
	const unread = $derived(!notification.is_read);
	const severity = $derived(getSeverityIcon(notification.severity));
	const TypeIcon = $derived(getTypeIcon(notification.type));
	const meta = $derived(notification.notification_metadata);

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onSelect(notification.id);
		}
	}
</script>

<div
	role="button"
	tabindex="0"
	onclick={() => onSelect(notification.id)}
	onkeydown={onKeydown}
	class={cn(
		'group relative flex cursor-pointer gap-3 text-left transition-colors outline-none hover:bg-accent/50 focus-visible:bg-accent/60',
		full ? 'rounded-lg border px-4 py-3' : 'px-4 py-2.5',
		!unread && 'opacity-70 hover:opacity-100 focus-visible:opacity-100'
	)}
>
	<span
		class={cn(
			'absolute top-2.5 bottom-2.5 w-0.5 rounded-full',
			full ? 'left-1.5' : 'left-0',
			unread ? severity.bar : 'bg-transparent'
		)}
	></span>

	<div
		class={cn(
			'mt-0.5 flex shrink-0 items-center justify-center rounded-md bg-muted',
			full ? 'size-8' : 'size-7',
			severity.class
		)}
	>
		<TypeIcon class={full ? 'size-4' : 'size-3.5'} />
	</div>

	<div class="min-w-0 flex-1">
		<div class="flex items-start gap-2">
			<p
				class={cn(
					'min-w-0 flex-1 leading-snug',
					full ? 'text-sm' : 'text-[13px]',
					unread ? 'font-medium text-foreground' : 'text-foreground/85',
					!full && 'line-clamp-1'
				)}
			>
				{notification.title}
			</p>
			<span
				class="shrink-0 pt-px font-mono text-[10px] text-muted-foreground tabular-nums transition-opacity group-hover:opacity-0 group-focus-within:opacity-0"
			>
				{relativeTime(notification.created_at)}
			</span>
			{#if unread}
				<span
					class="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary transition-opacity group-hover:opacity-0 group-focus-within:opacity-0"
				></span>
			{/if}
		</div>

		<p class={cn('mt-0.5 text-muted-foreground', full ? 'text-sm' : 'line-clamp-2 text-xs')}>
			{notification.message}
		</p>

		<div class="mt-1.5 flex items-center gap-2">
			<span class="text-[10px] font-medium tracking-[0.08em] text-muted-foreground/70 uppercase">
				{NOTIFICATION_TYPE_LABELS[notification.type]}
			</span>
			{#if meta?.action_label}
				<span class="text-muted-foreground/40">·</span>
				<button
					type="button"
					class="inline-flex items-center gap-0.5 text-[11px] font-medium text-primary hover:underline"
					onclick={(e) => onAction(notification.id, e)}
				>
					{meta.action_label}
					<ArrowUpRight class="size-3" />
				</button>
			{:else if meta?.url}
				<ArrowUpRight class="size-3 text-muted-foreground/60" />
			{/if}
		</div>
	</div>

	<div
		class={cn(
			'absolute top-2 right-3 flex items-center gap-0.5 rounded-md border p-0.5 shadow-sm transition-opacity',
			'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100',
			full ? 'bg-card' : 'bg-popover'
		)}
	>
		{#if unread}
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon-sm"
							class="size-6"
							onclick={(e: MouseEvent) => onMarkRead(notification.id, e)}
							aria-label="Mark as read"
						>
							<Check class="size-3" />
						</Button>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content side="bottom">Mark as read</Tooltip.Content>
			</Tooltip.Root>
		{/if}
		<Tooltip.Root>
			<Tooltip.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="icon-sm"
						class="size-6 text-muted-foreground hover:text-destructive"
						onclick={(e: MouseEvent) => onDelete(notification.id, e)}
						aria-label="Delete notification"
					>
						<Trash2 class="size-3" />
					</Button>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content side="bottom">Delete</Tooltip.Content>
		</Tooltip.Root>
	</div>
</div>
