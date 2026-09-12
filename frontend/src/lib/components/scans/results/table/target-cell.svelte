<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import { exactToken } from '$lib/utilities/scan-insights';

	interface Props {
		value?: string | null;
		values?: string[];
		onFilter?: (token: string) => void;
	}

	let { value = null, values, onFilter }: Props = $props();

	let list = $derived(values ?? (value ? [value] : []));
	let first = $derived(list[0] ?? '');
	let rest = $derived(list.length - 1);
</script>

{#if first}
	<div class="flex min-w-0 items-center gap-1">
		<Hint text={list.length > 1 ? list.join(', ') : `Filter to ${first}`}>
			{#snippet child(props)}
				<button
					{...props}
					type="button"
					class="min-w-0 truncate text-xs text-muted-foreground hover:text-foreground hover:underline"
					onclick={(event) => {
						event.stopPropagation();
						onFilter?.(exactToken('target', first));
					}}
				>
					{first}
				</button>
			{/snippet}
		</Hint>
		{#if rest > 0}
			<span class="shrink-0 text-2xs text-muted-foreground/70">+{rest}</span>
		{/if}
	</div>
{:else}
	<span class="text-xs text-muted-foreground/50">—</span>
{/if}
