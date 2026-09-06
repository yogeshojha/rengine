<script lang="ts">
	import ConfirmDialog from './confirm-dialog.svelte';

	interface Props {
		open: boolean;
		title?: string;
		description?: string;
		confirmLabel?: string;
		cancelLabel?: string;
		onOpenChange: (open: boolean) => void;
		onConfirm: () => void;
	}

	let {
		open = $bindable(),
		title = 'Discard unsaved changes?',
		description = 'Changes have not been saved. Leaving now discards them.',
		confirmLabel = 'Discard',
		cancelLabel = 'Keep editing',
		onOpenChange,
		onConfirm
	}: Props = $props();
</script>

<ConfirmDialog
	bind:open
	{title}
	{description}
	{confirmLabel}
	{cancelLabel}
	destructive
	{onOpenChange}
	{onConfirm}
/>
