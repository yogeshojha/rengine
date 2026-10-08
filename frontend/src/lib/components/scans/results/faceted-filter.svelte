<script lang="ts">
	import ListFilter from '@lucide/svelte/icons/list-filter';
	import Check from '@lucide/svelte/icons/check';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { cn } from '$lib/utils';
	import type { Facet } from '$lib/utilities/scan-insights';

	/** a facet option; leave out the count when the source has none */
	type Option = Omit<Facet, 'count'> & { count?: number };

	interface Props {
		title: string;
		options: Option[];
		selected: string[];
		onChange: (next: string[]) => void;
		/** shown but not usable yet, e.g. while its options load */
		disabled?: boolean;
	}

	let { title, options, selected, onChange, disabled = false }: Props = $props();
	let open = $state(false);

	function toggle(value: string) {
		onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
	}
</script>

<Popover.Root bind:open>
	<Popover.Trigger>
		{#snippet child({ props })}
			<Button
				{...props}
				variant="outline"
				{disabled}
				class={selected.length ? 'border-primary/50 bg-primary/5' : ''}
			>
				<ListFilter class="h-4 w-4" />
				{title}
				{#if selected.length}
					<Badge variant="secondary" class="h-5 px-1.5 text-xs">{selected.length}</Badge>
				{/if}
			</Button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-56 p-0" align="start">
		<Command.Root>
			<Command.Input placeholder={title} />
			<Command.List class="max-h-72">
				<Command.Empty>No matches</Command.Empty>
				<Command.Group>
					{#each options as option (option.value)}
						{@const isSel = selected.includes(option.value)}
						<Command.Item value={option.value} onSelect={() => toggle(option.value)}>
							<div
								class={cn(
									'flex size-4 items-center justify-center rounded-sm border',
									isSel
										? 'border-primary bg-primary text-primary-foreground'
										: 'border-muted-foreground/40 [&_svg]:invisible'
								)}
							>
								<Check class="size-3" />
							</div>
							<span class="truncate">{option.label}</span>
							{#if option.count != null}
								<span class="ml-auto text-xs text-muted-foreground tabular-nums"
									>{option.count.toLocaleString()}</span
								>
							{/if}
						</Command.Item>
					{/each}
				</Command.Group>
				{#if selected.length}
					<Command.Separator />
					<Command.Group>
						<Command.Item value="__clear" onSelect={() => onChange([])} class="justify-center">
							Clear
						</Command.Item>
					</Command.Group>
				{/if}
			</Command.List>
		</Command.Root>
	</Popover.Content>
</Popover.Root>
