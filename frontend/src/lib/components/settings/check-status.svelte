<script lang="ts">
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Hint from '$lib/components/hint.svelte';
	import { CHECK_DOT, type CheckState } from './status';

	interface Props {
		check: CheckState;
		label: string;
		message?: string | null;
		busy?: boolean;
		busyLabel?: string;
		muted?: boolean;
	}

	let {
		check,
		label,
		message = null,
		busy = false,
		busyLabel = '',
		muted = false
	}: Props = $props();
</script>

<Hint text={message}>
	{#snippet child(props)}
		<span {...props} class="inline-flex items-center gap-2 text-sm">
			{#if busy}
				<Spinner class="size-3" />
				<span class="text-muted-foreground">{busyLabel}</span>
			{:else}
				<span class="flex h-5 items-center">
					<span class="size-2 shrink-0 rounded-full {CHECK_DOT[check]}" aria-hidden="true"></span>
				</span>
				<span class={muted ? 'text-muted-foreground' : ''}>{label}</span>
			{/if}
		</span>
	{/snippet}
</Hint>
