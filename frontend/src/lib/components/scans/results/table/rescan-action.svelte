<script lang="ts">
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import { SURFACE, type SurfaceDimension } from '$lib/config/surface';

	interface Props {
		count: number;
		dimension: SurfaceDimension;
		noun?: string;
		nounPlural?: string;
		busy?: boolean;
		onRescan: () => void | Promise<void>;
	}

	let { count, dimension, noun, nounPlural, busy = false, onRescan }: Props = $props();

	const spec = $derived(SURFACE[dimension]);
	const label = $derived(count === 1 ? (noun ?? spec.noun) : (nounPlural ?? spec.nounPlural));

	let confirming = $state(false);

	async function confirm() {
		await onRescan();
		confirming = false;
	}
</script>

<LoadingButton
	variant="ghost"
	size="sm"
	loading={busy}
	loadingLabel="Starting"
	onclick={() => (confirming = true)}
>
	<RefreshCw class="h-3.5 w-3.5 text-muted-foreground" />
	Rescan
</LoadingButton>

<ConfirmDialog
	bind:open={confirming}
	title="Rescan {count.toLocaleString()} {label}"
	confirmLabel="Rescan"
	loadingLabel="Starting"
	loading={busy}
	onOpenChange={(value) => (confirming = value)}
	onConfirm={confirm}
/>
