<script lang="ts">
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Button } from '$lib/components/ui/button';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import { relativeTimeLong } from '$lib/utilities/dates';
	import { detailLines, SEVERITY_TILE_CLASS } from '$lib/utilities/notifications';
	import { getTypeIcon } from '$lib/utilities/notification-icons';
	import { NOTIFICATION_TYPE_LABELS, type Notification } from '$lib/types/notification';
	import { cn } from '$lib/utils';

	interface Props {
		notification: Notification | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		onOpen: () => void;
	}

	let { notification, open, onOpenChange, onOpen }: Props = $props();

	const TypeIcon = $derived(notification ? getTypeIcon(notification.type) : null);
	const lines = $derived(notification ? detailLines(notification.message) : []);
	const meta = $derived(notification?.notification_metadata);
	let contentEl = $state<HTMLElement | null>(null);
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content
		bind:ref={contentEl}
		side="right"
		tabindex={-1}
		class="flex w-full flex-col gap-0 p-0 outline-none sm:max-w-md"
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			contentEl?.focus();
		}}
	>
		{#if notification && TypeIcon}
			<Sheet.Header class="gap-3 border-b px-5 py-4 pr-12">
				<div class="flex items-start gap-3">
					<div
						class={cn(
							'flex size-8 shrink-0 items-center justify-center rounded-md',
							SEVERITY_TILE_CLASS[notification.severity]
						)}
					>
						<TypeIcon class="size-4" />
					</div>
					<div class="min-w-0 flex-1">
						<Sheet.Title class="leading-snug wrap-anywhere">
							{notification.title}
						</Sheet.Title>
						<Sheet.Description class="mt-0.5">
							{NOTIFICATION_TYPE_LABELS[notification.type]} · {relativeTimeLong(
								notification.created_at
							)}
						</Sheet.Description>
					</div>
				</div>
			</Sheet.Header>

			{#if lines.length > 0}
				<ScrollArea class="min-h-0 flex-1">
					<div class="divide-y divide-border px-5">
						{#each lines as line, i (i)}
							<p class="py-2.5 text-sm text-foreground wrap-anywhere">{line}</p>
						{/each}
					</div>
				</ScrollArea>
			{:else}
				<div class="flex-1"></div>
			{/if}

			{#if meta?.url}
				<Sheet.Footer class="flex-row justify-end gap-2 border-t px-5 py-3">
					<Button size="sm" onclick={onOpen}>
						Open
						<ArrowUpRight class="size-4" />
					</Button>
				</Sheet.Footer>
			{/if}
		{/if}
	</Sheet.Content>
</Sheet.Root>
