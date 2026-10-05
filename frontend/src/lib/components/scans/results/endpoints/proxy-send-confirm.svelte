<script lang="ts">
	import { untrack } from 'svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Label } from '$lib/components/ui/label';
	import { proxyTool } from '$lib/stores/proxy-tool.svelte';

	let skip = $state(false);
	let title = $state('');
	let note = $state<string | null>(null);

	const open = $derived(proxyTool.pending !== null);

	$effect.pre(() => {
		const pending = proxyTool.pending;
		if (!pending) return;
		untrack(() => {
			title = pending.title;
			note = pending.note;
			skip = false;
		});
	});
</script>

<ConfirmDialog
	{open}
	{title}
	description={note ?? undefined}
	confirmLabel="Send"
	onOpenChange={(next) => {
		if (!next) proxyTool.settle(false);
	}}
	onConfirm={() => proxyTool.settle(true, skip)}
>
	<div class="flex items-center gap-2">
		<Checkbox id="proxy-send-skip" bind:checked={skip} />
		<Label for="proxy-send-skip" class="font-normal">Don't ask again</Label>
	</div>
</ConfirmDialog>
