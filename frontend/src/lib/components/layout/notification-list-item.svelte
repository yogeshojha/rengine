<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import Trash from '@lucide/svelte/icons/trash';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import { relativeTime } from '$lib/utilities/dates.js';
	import { getSeverityIcon, getTypeIcon } from '$lib/utilities/notification-icons';
	import type { Notification } from '$lib/types/notification';

	interface Props {
		notification: Notification;
		variant?: 'compact' | 'full';
		onSelect: (id: number) => void;
		onAction: (id: number, event: Event) => void;
		onDelete: (id: number, event: Event) => void;
	}

	let { notification, variant = 'compact', onSelect, onAction, onDelete }: Props = $props();

	const full = $derived(variant === 'full');
	const iconData = $derived(getSeverityIcon(notification.severity));
	const TypeIcon = $derived(getTypeIcon(notification.type));
</script>

<button
	type="button"
	class="flex items-start gap-3 cursor-pointer group w-full text-left transition-colors hover:bg-muted/50 {full
		? 'p-4 rounded-lg border'
		: 'p-3 my-1 rounded-md'} {!notification.is_read
		? full
			? 'bg-muted/30 border-l-4 border-l-chart-1'
			: 'bg-muted/30'
		: ''}"
	onclick={() => onSelect(notification.id)}
>
	<div class="mt-0.5">
		<iconData.icon class="{full ? 'h-5 w-5' : 'h-4 w-4'} {iconData.class}" />
	</div>
	<div class="flex-1 min-w-0 {full ? 'space-y-2' : 'space-y-1'}">
		{#if full}
			<div class="flex items-start justify-between gap-2">
				<p class="text-sm font-medium leading-none">{notification.title}</p>
				<div class="flex items-center gap-1 shrink-0">
					<TypeIcon class="h-3.5 w-3.5 text-muted-foreground" />
					<Badge variant="outline" class="text-xs">{notification.type}</Badge>
				</div>
			</div>
			<p class="text-sm text-muted-foreground">{notification.message}</p>
		{:else}
			<p class="text-sm font-medium leading-none truncate">{notification.title}</p>
			<p class="text-xs text-muted-foreground line-clamp-2">{notification.message}</p>
		{/if}
		<div class="flex items-center gap-2">
			<span class="text-xs text-muted-foreground">{relativeTime(notification.created_at)}</span>
			{#if notification.notification_metadata?.url}
				<ExternalLink class="h-3 w-3 text-muted-foreground" />
			{/if}
		</div>
		{#if notification.notification_metadata?.action_label}
			<Button
				variant="secondary"
				size="sm"
				class={full ? 'h-7 text-xs' : 'h-6 text-xs mt-2'}
				onclick={(e) => onAction(notification.id, e)}
			>
				{notification.notification_metadata.action_label}
				<ExternalLink class="{full ? 'ml-1.5' : 'ml-1'} h-3 w-3" />
			</Button>
		{/if}
	</div>
	<div class="flex items-center gap-1">
		{#if !notification.is_read}
			<div class="h-2 w-2 rounded-full bg-chart-1"></div>
		{/if}
		<Button
			variant="ghost"
			size="icon"
			class="{full
				? 'h-8 w-8'
				: 'h-6 w-6'} opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
			onclick={(e) => onDelete(notification.id, e)}
		>
			<Trash class={full ? 'h-4 w-4' : 'h-3 w-3'} />
			<span class="sr-only">Delete notification</span>
		</Button>
	</div>
</button>
