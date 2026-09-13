<script lang="ts">
	import type { Target } from '$lib/types/target';
	import * as Dialog from '$lib/components/ui/dialog';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import History from '@lucide/svelte/icons/history';
	import CopyButton from '@/components/copy-button.svelte';
	import ScanHistoryTable from '$lib/components/scans/scan-history-table.svelte';

	interface Props {
		open: boolean;
		target: Target | null;
		onOpenChange: (open: boolean) => void;
	}

	let { open = $bindable(), target, onOpenChange }: Props = $props();
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content
		class="flex max-h-[88vh] flex-col gap-0 p-0 sm:max-w-5xl"
		onOpenAutoFocus={(e) => e.preventDefault()}
	>
		{#if target}
			<Dialog.Header class="gap-1 border-b px-6 pt-5 pr-12 pb-4">
				<div class="flex items-center gap-2.5">
					<span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted">
						<History class="size-4 text-muted-foreground" />
					</span>
					<Dialog.Title class="text-base font-semibold">Scan history</Dialog.Title>
				</div>
				<Dialog.Description class="flex items-center gap-1.5">
					<code class="truncate font-mono text-xs">{target.target_value}</code>
					<CopyButton value={target.target_value} />
				</Dialog.Description>
			</Dialog.Header>

			<ScrollArea
				class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(88vh-7rem)]"
			>
				<div class="p-4">
					<ScanHistoryTable targetId={target.id} />
				</div>
			</ScrollArea>
		{/if}
	</Dialog.Content>
</Dialog.Root>
