<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { Spinner } from '$lib/components/ui/spinner';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import type { IconComponent } from '$lib/config/icons';

	interface Props {
		open: boolean;
		title: string;
		description?: string;
		confirmLabel?: string;
		cancelLabel?: string;
		destructive?: boolean;
		loading?: boolean;
		loadingLabel?: string;
		icon?: IconComponent | null;
		onOpenChange: (open: boolean) => void;
		onConfirm: () => void;
	}

	let {
		open = $bindable(),
		title,
		description,
		confirmLabel = 'Continue',
		cancelLabel = 'Cancel',
		destructive = false,
		loading = false,
		loadingLabel = 'Working…',
		icon,
		onOpenChange,
		onConfirm
	}: Props = $props();

	const HeadIcon = $derived(icon ?? (destructive ? TriangleAlert : null));
</script>

<AlertDialog.Root {open} {onOpenChange}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<div class="flex items-center gap-3">
				{#if HeadIcon}
					<div
						class="flex items-center justify-center rounded-full p-2 {destructive
							? 'bg-destructive/10 text-destructive'
							: 'bg-muted text-muted-foreground'}"
					>
						<HeadIcon class="h-5 w-5" />
					</div>
				{/if}
				<div>
					<AlertDialog.Title>{title}</AlertDialog.Title>
					{#if description}
						<AlertDialog.Description class="mt-1">{description}</AlertDialog.Description>
					{/if}
				</div>
			</div>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel disabled={loading}>{cancelLabel}</AlertDialog.Cancel>
			<Button
				variant={destructive ? 'destructive' : 'default'}
				onclick={onConfirm}
				disabled={loading}
				class="gap-2"
			>
				{#if loading}
					<Spinner class="h-4 w-4" />
					{loadingLabel}
				{:else}
					{confirmLabel}
				{/if}
			</Button>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
