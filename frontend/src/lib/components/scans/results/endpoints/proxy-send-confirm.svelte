<script lang="ts">
	import { untrack } from 'svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Label } from '$lib/components/ui/label';
	import { proxyTool } from '$lib/stores/proxy-tool.svelte';

	let skip = $state(false);

	const pending = $derived(proxyTool.pending);

	$effect.pre(() => {
		if (pending) untrack(() => (skip = false));
	});
</script>

{#if pending}
	<ConfirmDialog
		open
		title={pending.title}
		description={pending.description}
		confirmLabel="Send"
		onOpenChange={(next) => {
			if (!next) proxyTool.settle(false);
		}}
		onConfirm={() => proxyTool.settle(true, skip)}
	>
		<div class="flex items-center gap-2">
			<Checkbox id="proxy-send-skip" bind:checked={skip} />
			<Label for="proxy-send-skip" class="font-normal">Do not ask again</Label>
		</div>
	</ConfirmDialog>
{/if}
