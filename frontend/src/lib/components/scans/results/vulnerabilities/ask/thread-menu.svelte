<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Eraser from '@lucide/svelte/icons/eraser';
	import History from '@lucide/svelte/icons/history';
	import Plus from '@lucide/svelte/icons/plus';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { relativeTime } from '$lib/utilities/dates';
	import type { AskThread } from '$lib/types/ask';

	interface Props {
		threads: AskThread[];
		active: AskThread | null;
		onPick: (thread: AskThread) => void;
		onNew: () => void;
		onClear: () => void;
	}

	let { threads, active, onPick, onNew, onClear }: Props = $props();
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="ghost" size="sm" class="h-7 max-w-56 gap-1.5 px-2 text-xs">
				<History />
				<span class="truncate">{active?.title ?? 'New thread'}</span>
				{#if threads.length > 1}
					<span class="font-mono text-2xs text-muted-foreground tabular-nums">{threads.length}</span
					>
				{/if}
				<ChevronDown />
			</Button>
		{/snippet}
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align="start" class="w-72 max-h-none overflow-visible">
		{#if threads.length}
			<ScrollArea class="max-h-64">
				<DropdownMenu.Group>
					{#each threads as thread (thread.id)}
						<DropdownMenu.Item
							class="flex flex-col items-start gap-0.5"
							data-active={thread.id === active?.id || undefined}
							onclick={() => onPick(thread)}
						>
							<span class="w-full truncate text-sm">{thread.title}</span>
							<span class="text-2xs text-muted-foreground">
								{thread.message_count}
								{thread.message_count === 1 ? 'message' : 'messages'} · {relativeTime(
									thread.last_at
								)}
							</span>
						</DropdownMenu.Item>
					{/each}
				</DropdownMenu.Group>
			</ScrollArea>
			<DropdownMenu.Separator />
		{/if}
		<DropdownMenu.Group>
			<DropdownMenu.Item onclick={onNew}>
				<Plus />
				New thread
			</DropdownMenu.Item>
			{#if threads.length}
				<DropdownMenu.Item variant="destructive" onclick={onClear}>
					<Eraser />
					Clear history on this finding
				</DropdownMenu.Item>
			{/if}
		</DropdownMenu.Group>
	</DropdownMenu.Content>
</DropdownMenu.Root>
