<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { TriangleAlert, LoaderCircle } from 'lucide-svelte';

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
		title = 'Delete Item',
		description = 'Are you sure you want to delete this item? This action cannot be undone.',
		confirmLabel = 'Delete',
		isDeleting = false,
		onOpenChange,
		onConfirm
	}: Props = $props();
</script>

<AlertDialog.Root {open} {onOpenChange}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<div class="flex items-center gap-3">
				<div class="rounded-full bg-destructive/10 flex items-center justify-center p-2">
					<TriangleAlert class="h-5 w-5 text-destructive" />
				</div>
				<div>
					<AlertDialog.Title>{title}</AlertDialog.Title>
					<AlertDialog.Description class="mt-1">
						{description}
					</AlertDialog.Description>
				</div>
			</div>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel disabled={isDeleting}>Cancel</AlertDialog.Cancel>
			<Button variant="destructive" onclick={onConfirm} disabled={isDeleting} class="gap-2">
				{#if isDeleting}
					<LoaderCircle class="h-4 w-4 animate-spin" />
					Deleting...
				{:else}
					{confirmLabel}
				{/if}
			</Button>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
