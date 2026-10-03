<script lang="ts">
	import Lock from '@lucide/svelte/icons/lock';
	import Hint from '$lib/components/hint.svelte';

	let { reason }: { reason: string } = $props();
</script>

<Hint text={reason}>
	{#snippet child(props)}
		<span
			{...props}
			role="img"
			aria-label={reason}
			class="pointer-events-auto ms-auto flex items-center"
		>
			<Lock class="size-3.5" />
		</span>
	{/snippet}
</Hint>
