<script lang="ts">
	import FolderTree from '@lucide/svelte/icons/folder-tree';

	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import HostStructure from './host-structure.svelte';
	import type { EndpointSummary } from '$lib/utilities/endpoints';

	interface Props {
		host: string | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		projectId: string;
		scanId: string;
		onOpenEndpoints?: (host: string) => void;
	}

	let { host, open, onOpenChange, projectId, scanId, onOpenEndpoints }: Props = $props();

	let summary = $state<EndpointSummary | null>(null);

	const n = (value: number) => value.toLocaleString();
	let line = $derived.by(() => {
		if (!summary || !summary.total) return 'Every path discovered on this host.';
		const parts = [
			`${n(summary.total)} ${summary.total === 1 ? 'endpoint' : 'endpoints'}`,
			`${n(summary.probed)} verified`
		];
		if (summary.with_params) parts.push(`${n(summary.with_params)} take input`);
		if (summary.interesting) parts.push(`${n(summary.interesting)} worth testing`);
		return parts.join(' · ');
	});
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="flex max-h-[88vh] flex-col gap-0 p-0 sm:max-w-5xl">
		{#if host}
			<Dialog.Header class="gap-1 border-b px-6 pt-5 pr-12 pb-4">
				<div class="flex items-center gap-2.5">
					<span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted">
						<FolderTree class="size-4" />
					</span>
					<Dialog.Title class="font-mono text-base font-semibold break-all">{host}</Dialog.Title>
				</div>
				<Dialog.Description class="tabular-nums">{line}</Dialog.Description>
			</Dialog.Header>

			<ScrollArea
				class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(88vh-12rem)]"
			>
				<HostStructure
					{host}
					{projectId}
					{scanId}
					onSummary={(s) => (summary = s)}
					onOpenEndpoints={onOpenEndpoints
						? (h) => {
								onOpenChange(false);
								onOpenEndpoints(h);
							}
						: undefined}
				/>
			</ScrollArea>

			<div class="flex items-center justify-end gap-2 border-t px-6 py-3">
				<Button variant="outline" size="sm" onclick={() => onOpenChange(false)}>Done</Button>
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
