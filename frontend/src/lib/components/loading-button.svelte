<script lang="ts">
	import type { ComponentProps } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';

	type ButtonProps = ComponentProps<typeof Button>;

	interface Props extends ButtonProps {
		loading?: boolean;
		loadingLabel?: string;
	}

	let { loading = false, loadingLabel, disabled = false, children, ...rest }: Props = $props();
</script>

<Button {...rest} disabled={disabled || loading}>
	{#if loading}
		<Spinner class="mr-2" />
		{loadingLabel ?? ''}
	{:else}
		{@render children?.()}
	{/if}
</Button>
