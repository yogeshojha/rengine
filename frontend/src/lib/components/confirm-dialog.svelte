<script lang="ts">
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import type { Snippet } from 'svelte';

	interface Props {
		open: boolean;
		title: string;
		description?: string;
		confirmLabel?: string;
		cancelLabel?: string;
		destructive?: boolean;
		loading?: boolean;
		loadingLabel?: string;
		onOpenChange: (open: boolean) => void;
		onConfirm: () => void;
		children?: Snippet;
	}

	let {
		open = $bindable(),
		title,
		description,
		confirmLabel = 'Continue',
		cancelLabel = 'Cancel',
		destructive = false,
		loading = false,
		loadingLabel = 'Working',
		onOpenChange,
		onConfirm,
		children
	}: Props = $props();
</script>

<AlertDialog.Root bind:open={() => open, (next) => onOpenChange(next)}>
	<AlertDialog.Content escapeKeydownBehavior={loading ? 'ignore' : 'close'}>
		<AlertDialog.Header>
			<div class="flex items-center gap-3">
				{#if destructive}
					<div
						class="flex items-center justify-center rounded-full bg-destructive/10 p-2 text-destructive"
					>
						<TriangleAlert class="h-5 w-5" />
					</div>
				{/if}
				<div class="min-w-0">
					<AlertDialog.Title>{title}</AlertDialog.Title>
					{#if description}
						<AlertDialog.Description class="mt-1 wrap-anywhere"
							>{description}</AlertDialog.Description
						>
					{/if}
				</div>
			</div>
		</AlertDialog.Header>
		{@render children?.()}
		<AlertDialog.Footer>
			<AlertDialog.Cancel disabled={loading}>{cancelLabel}</AlertDialog.Cancel>
			<LoadingButton
				variant={destructive ? 'destructive' : 'default'}
				onclick={onConfirm}
				{loading}
				{loadingLabel}
			>
				{confirmLabel}
			</LoadingButton>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
