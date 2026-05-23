<script lang="ts">
	import { Check, Copy, X } from 'lucide-svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Tooltip from '$lib/components/ui/tooltip';

	interface Props {
		value: string;
		class?: string;
	}

	let { value, class: className = '' }: Props = $props();

	let copied = $state(false);
	let failed = $state(false);

	async function copy() {
		try {
			await navigator.clipboard.writeText(value);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {
			failed = true;
			setTimeout(() => (failed = false), 2000);
		}
	}
</script>

<Tooltip.Root ignoreNonKeyboardFocus>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<Button
				{...props}
				variant="ghost"
				size="icon"
				class="h-7 w-7 shrink-0 {className}"
				onclick={copy}
			>
				{#if copied}
					<Check class="h-3.5 w-3.5 text-green-500" />
				{:else if failed}
					<X class="h-3.5 w-3.5 text-destructive" />
				{:else}
					<Copy class="h-3.5 w-3.5 text-muted-foreground" />
				{/if}
			</Button>
		{/snippet}
	</Tooltip.Trigger>

	<Tooltip.Content>
		<p>{copied ? 'Copied!' : failed ? 'Failed to copy' : 'Copy'}</p>
	</Tooltip.Content>
</Tooltip.Root>
