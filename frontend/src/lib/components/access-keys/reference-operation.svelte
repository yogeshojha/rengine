<script lang="ts">
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Badge } from '$lib/components/ui/badge';
	import CodeBlock from '$lib/components/code-block.svelte';
	import { LEVEL_BADGE, LEVEL_LABELS } from '$lib/config/access-keys';
	import { METHOD_TONE } from '$lib/config/api-reference';
	import { requestFor } from '$lib/utilities/access-keys';
	import type { ReferenceOperation } from '$lib/types/access-key';
	import { PARAMETER_COL } from './columns';

	interface Props {
		operation: ReferenceOperation;
		origin: string;
	}

	let { operation, origin }: Props = $props();

	const ROW = 'grid grid-cols-[0.875rem_3.5rem_minmax(0,1fr)_auto] gap-x-3 px-4';

	let open = $state(false);

	const curl = $derived(open ? requestFor(operation.curl, origin) : '');
	const body = $derived(
		open && operation.example !== null && operation.example !== undefined
			? JSON.stringify(operation.example, null, 2)
			: ''
	);
</script>

<Collapsible.Root bind:open class="border-b border-border/60 last:border-b-0">
	<Collapsible.Trigger
		class="{ROW} w-full items-start py-2.5 text-left transition-colors hover:bg-muted/30 focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:outline-none"
	>
		<span class="flex h-5 items-center">
			<ChevronRightIcon class="size-3.5 text-muted-foreground {open ? 'rotate-90' : ''}" />
		</span>
		<span class="flex h-5 items-center">
			<Badge
				variant="outline"
				class="font-mono tracking-wide uppercase {METHOD_TONE[operation.method.toUpperCase()] ??
					''}"
			>
				{operation.method}
			</Badge>
		</span>
		<span class="flex min-w-0 flex-col gap-0.5">
			<span class="font-mono text-sm leading-5 wrap-anywhere">{operation.path}</span>
			<span class="text-xs text-muted-foreground">{operation.summary}</span>
		</span>
		<Badge variant={LEVEL_BADGE[operation.access]}>
			{LEVEL_LABELS[operation.access]}
		</Badge>
	</Collapsible.Trigger>
	<Collapsible.Content>
		<div class="{ROW} pt-1 pb-4">
			<div class="col-span-full flex min-w-0 flex-col gap-4 sm:col-[3/-1]">
				{#if operation.parameters.length}
					<div class="overflow-hidden rounded-md border" role="table" aria-label="Parameters">
						<div
							class="flex gap-3 border-b bg-muted/20 px-3 py-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
							role="row"
						>
							<span class={PARAMETER_COL.name} role="columnheader">Parameter</span>
							<span class={PARAMETER_COL.location} role="columnheader">In</span>
							<span class={PARAMETER_COL.type} role="columnheader">Type</span>
							<span class="hidden {PARAMETER_COL.description} sm:block" role="columnheader"
								>Description</span
							>
						</div>
						{#each operation.parameters as param (`${param.location}:${param.name}`)}
							<div
								class="flex flex-wrap gap-x-3 border-b border-border/60 px-3 py-1.5 last:border-b-0 sm:flex-nowrap"
								role="row"
							>
								<span
									class="{PARAMETER_COL.name} font-mono text-xs leading-5 wrap-anywhere"
									role="cell"
								>
									{param.name}
									{#if param.required}
										<span class="font-sans text-2xs text-muted-foreground">required</span>
									{/if}
								</span>
								<span
									class="{PARAMETER_COL.location} text-xs leading-5 text-muted-foreground"
									role="cell"
								>
									{param.location}
								</span>
								<span class="{PARAMETER_COL.type} font-mono text-xs leading-5" role="cell"
									>{param.type}</span
								>
								<span
									class="{PARAMETER_COL.description} basis-full text-xs leading-5 text-muted-foreground wrap-anywhere sm:basis-0 sm:text-foreground"
									role="cell"
								>
									{param.description ?? ''}
								</span>
							</div>
						{/each}
					</div>
				{/if}
				{#if body}
					<CodeBlock code={body} lang="json" label="Body" numbers={false} />
				{/if}
				<CodeBlock code={curl} lang="shell" label="Request" numbers={false} />
			</div>
		</div>
	</Collapsible.Content>
</Collapsible.Root>
