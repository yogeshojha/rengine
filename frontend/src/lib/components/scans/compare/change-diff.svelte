<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CodeBlock from '$lib/components/code-block.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import CheckCheck from '@lucide/svelte/icons/check-check';
	import { compareApi } from '$lib/api/compare';
	import { COMPARE_TAB_ALL } from '$lib/config/compare';
	import type { ChangeVerb } from '$lib/types/compare';

	interface Props {
		projectId: string;
		current: string;
		baseline: string;
		dimension: string;
		verbs: ChangeVerb[];
		filename: string;
	}

	let { projectId, current, baseline, dimension, verbs, filename }: Props = $props();

	let text = $state('');
	let loading = $state(true);
	let error = $state<string | null>(null);

	$effect(() => {
		const args = {
			projectId,
			current,
			baseline,
			dimension: dimension === COMPARE_TAB_ALL ? undefined : dimension,
			verbs
		};
		let live = true;
		loading = true;
		error = null;
		compareApi
			.diff(args)
			.then((body) => {
				if (live) text = body;
			})
			.catch((e) => {
				if (live) error = e instanceof Error ? e.message : 'Could not load the diff.';
			})
			.finally(() => {
				if (live) loading = false;
			});
		return () => {
			live = false;
		};
	});

	let empty = $derived(!loading && !error && !text.includes('@@'));
</script>

{#if loading}
	<div class="p-4 sm:p-5"><Skeleton class="h-72" /></div>
{:else if error}
	<EmptyState title="Could not load the diff" description={error} class="m-4 sm:m-5" compact />
{:else if empty}
	<EmptyState
		icon={CheckCheck}
		title="Nothing changed"
		description="No line to show."
		class="m-4 sm:m-5"
		compact
	/>
{:else}
	<div class="p-4 sm:p-5">
		<CodeBlock
			code={text}
			lang="diff"
			label="Unified diff"
			numbers={false}
			maxLines={40}
			maxHeight="calc(100svh - 30rem)"
			download={filename}
		/>
	</div>
{/if}
