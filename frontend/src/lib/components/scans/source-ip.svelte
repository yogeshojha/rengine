<script lang="ts">
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import Hint from '$lib/components/hint.svelte';
	import { sourceIpView } from '$lib/utilities/source-ip';
	import { cn } from '$lib/utils';
	import type { ScanRead } from '$lib/types/scan';

	interface Props {
		scan: Pick<ScanRead, 'status' | 'source_ip'>;
		class?: string;
	}

	let { scan, class: className }: Props = $props();

	let view = $derived(sourceIpView(scan));
</script>

{#if view.kind === 'checking'}
	<span class={cn('text-muted-foreground', className)}>Checking</span>
{:else if view.kind === 'not_measured'}
	<Hint text={view.reason}>
		{#snippet child(props)}
			<span {...props} class={cn('text-muted-foreground', className)}>Not measured</span>
		{/snippet}
	</Hint>
{:else if view.kind === 'measured'}
	<span class={cn('inline-flex min-w-0 flex-wrap items-center gap-x-3 gap-y-0.5', className)}>
		{#each view.rows as row (row.family)}
			<span class="inline-flex min-w-0 items-center gap-1.5">
				<span class="font-mono text-foreground">{row.address}</span>
				{#if row.changedTo}
					<Hint text="Start of scan, then end of scan">
						{#snippet child(props)}
							<span {...props} class="flex h-5 items-center">
								<ArrowRight class="size-3 text-muted-foreground" aria-label="then" />
							</span>
						{/snippet}
					</Hint>
					<span class="font-mono text-foreground">{row.changedTo}</span>
				{/if}
			</span>
		{/each}
		{#if view.proxied}
			<span class="text-xs text-muted-foreground">via proxy</span>
		{/if}
		{#if view.endFailure}
			<Hint text={view.endFailure}>
				{#snippet child(props)}
					<span {...props} class="text-xs text-muted-foreground">End not measured</span>
				{/snippet}
			</Hint>
		{/if}
	</span>
{/if}
