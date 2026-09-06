<script lang="ts">
	import ConfirmDialog from './confirm-dialog.svelte';

	interface Props {
		open: boolean;
		title?: string;
		description?: string;
		confirmLabel?: string;
		isDeleting?: boolean;
		onOpenChange: (open: boolean) => void;
		onConfirm: () => void;
	}

	let {
		open = $bindable(),
		title = 'Delete this item?',
		description = 'The item and everything stored with it are removed.',
		confirmLabel = 'Delete',
		isDeleting = false,
		onOpenChange,
		onConfirm
	}: Props = $props();
</script>

<ConfirmDialog
	bind:open
	{title}
	{description}
	{confirmLabel}
	destructive
	loading={isDeleting}
	loadingLabel="Deleting…"
	{onOpenChange}
	{onConfirm}
/>
