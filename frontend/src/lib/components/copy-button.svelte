<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import Copy from '@lucide/svelte/icons/copy';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { cn } from '$lib/utils';
	import { writeClipboard } from '$lib/utilities/clipboard';

	interface Props {
		value: string;
		class?: string;
	}

	let { value, class: className = '' }: Props = $props();

	let copied = $state(false);
	let failed = $state(false);

	async function copy(e?: MouseEvent) {
		e?.stopPropagation();
		if (await writeClipboard(value)) {
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} else {
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
				class={cn('size-7 shrink-0', className)}
				aria-label="Copy"
				onclick={(e) => copy(e)}
			>
				{#if copied}
					<Check class="h-3.5 w-3.5 text-foreground" />
				{:else if failed}
					<X class="h-3.5 w-3.5 text-destructive" />
				{:else}
					<Copy class="h-3.5 w-3.5 text-muted-foreground" />
				{/if}
			</Button>
		{/snippet}
	</Tooltip.Trigger>

	<Tooltip.Content>
		<p>{copied ? 'Copied' : failed ? 'Copy failed' : 'Copy'}</p>
	</Tooltip.Content>
</Tooltip.Root>
