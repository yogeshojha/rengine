<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import { STATUS_CLASS_FILL, statusClassOf } from '$lib/config/endpoints';

	interface Props {
		status: number | null;
		probed: boolean;
	}

	let { status, probed }: Props = $props();
	let klass = $derived(statusClassOf(status));
</script>

{#if !probed}
	<Hint text="This scan did not request this endpoint, so its status is unknown.">
		{#snippet child(props)}
			<span {...props} class="flex h-5 shrink-0 items-center gap-1.5 text-xs text-muted-foreground">
				<span class="size-1.5 rounded-full border border-dashed border-muted-foreground/60"></span>
				<span class="italic">not checked</span>
			</span>
		{/snippet}
	</Hint>
{:else}
	<span class="flex h-5 shrink-0 items-center gap-1.5">
		<span class="size-1.5 rounded-full" style="background:{STATUS_CLASS_FILL[klass]}"></span>
		<span class="font-mono text-xs tabular-nums">{status ?? '—'}</span>
	</span>
{/if}
