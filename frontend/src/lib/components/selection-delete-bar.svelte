<script lang="ts">
	import type { Snippet } from 'svelte';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import SelectionActionBar from './selection-action-bar.svelte';
	import ConfirmDialog from './confirm-dialog.svelte';

	interface Props {
		ids: string[];
		noun: string;
		nounPlural?: string;
		removes?: string;
		remove: (id: string) => Promise<unknown>;
		onDone?: () => void | Promise<void>;
		onClear: () => void;
		children?: Snippet;
	}

	let { ids, noun, nounPlural, removes, remove, onDone, onClear, children }: Props = $props();

	const many = $derived(nounPlural ?? `${noun}s`);
	const count = $derived(ids.length);
	const label = $derived(count === 1 ? noun : many);
	const body = $derived(
		removes
			? `${count.toLocaleString()} ${label} and ${count === 1 ? 'its' : 'their'} ${removes} are removed.`
			: `${count.toLocaleString()} ${label} ${count === 1 ? 'is' : 'are'} removed.`
	);

	let confirming = $state(false);
	let removing = $state(false);

	async function run() {
		const doomed = [...ids];
		removing = true;
		let done = 0;
		for (const id of doomed) {
			try {
				await remove(id);
				done += 1;
			} catch {
				/* counted as a miss below */
			}
		}
		removing = false;
		confirming = false;
		if (done) toast.success(`${done.toLocaleString()} ${done === 1 ? noun : many} deleted`);
		if (done < doomed.length) {
			const left = doomed.length - done;
			toast.error(`${left.toLocaleString()} ${left === 1 ? noun : many} not deleted.`);
		}
		await onDone?.();
	}
</script>

<SelectionActionBar selectedCount={count} {noun} nounPlural={many} {onClear}>
	{#if children}{@render children()}{/if}
	<Button
		variant="ghost"
		size="sm"
		class="gap-2 font-medium text-destructive hover:bg-destructive/10 hover:text-destructive"
		onclick={() => (confirming = true)}
	>
		<Trash2 class="h-3.5 w-3.5" />
		Delete
	</Button>
</SelectionActionBar>

<ConfirmDialog
	bind:open={confirming}
	title="Delete {count.toLocaleString()} {label}"
	description={body}
	confirmLabel="Delete"
	loadingLabel="Deleting"
	destructive
	loading={removing}
	onOpenChange={(value) => (confirming = value)}
	onConfirm={run}
/>
