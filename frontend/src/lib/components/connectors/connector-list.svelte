<script lang="ts">
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import PanelHead from '$lib/components/panel-head.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { connectors } from '$lib/stores/connectors.svelte';
	import { CONNECTOR_STATE_DOT, CONNECTOR_STATE_LABELS } from '$lib/config/connectors';
	import { relativeTime } from '$lib/utilities/dates';
	import type { Connector } from '$lib/types/connector';

	let { selectedId, projectId }: { selectedId: string | null; projectId: string } = $props();

	let pending = $state<Connector | null>(null);
	let deleting = $state(false);

	const items = $derived(connectors.items);
	const live = $derived(items.filter((c) => c.state === 'live').length);

	async function remove() {
		if (!pending) return;
		deleting = true;
		try {
			await connectorsApi.remove(pending.id, projectId);
			connectors.drop(pending.id);
			pending = null;
		} finally {
			deleting = false;
		}
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead title="Connectors" class="px-4 py-3">
		{#if live}
			<span class="text-success flex items-center gap-1.5">
				<span class="bg-success size-1.5 rounded-full" aria-hidden="true"></span>
				{live} receiving
			</span>
		{:else}
			<span class="tabular-nums">{items.length}</span>
		{/if}
	</PanelHead>

	<div class="divide-y">
		{#each items as item (item.id)}
			<div
				class="group hover:bg-muted/40 relative transition-colors {selectedId === item.id
					? 'bg-muted/50'
					: ''}"
			>
				<button
					type="button"
					class="w-full cursor-pointer px-4 py-3 text-left"
					onclick={() => connectors.select(item.id)}
				>
					<div class="flex items-center gap-2">
						<span class="size-1.5 shrink-0 rounded-full {CONNECTOR_STATE_DOT[item.state]}"></span>
						<span class="min-w-0 flex-1 truncate pr-6 text-sm font-medium">{item.name}</span>
						{#if item.queued > 0}
							<span
								class="text-primary shrink-0 text-xs font-medium tabular-nums group-hover:invisible"
								>{item.queued}</span
							>
						{/if}
					</div>
					<p class="text-muted-foreground mt-1 text-xs">
						{CONNECTOR_STATE_LABELS[item.state]}
						{#if item.last_seen_at}· {relativeTime(item.last_seen_at)}{/if}
					</p>
				</button>
				<Hint text="Delete connector">
					{#snippet child(props)}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="text-muted-foreground hover:text-destructive absolute top-2.5 right-2 size-6 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
							onclick={() => (pending = item)}
						>
							<Trash2Icon class="size-3.5" />
							<span class="sr-only">Delete {item.name}</span>
						</Button>
					{/snippet}
				</Hint>
			</div>
		{/each}
	</div>
</Card.Root>

<DeleteConfirmationDialog
	open={pending !== null}
	title="Delete {pending?.name ?? 'connector'}"
	description="The connector, its token and its request shapes are removed. Recorded endpoints are kept."
	isDeleting={deleting}
	onOpenChange={(value) => {
		if (!value) pending = null;
	}}
	onConfirm={remove}
/>
