<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Check from '@lucide/svelte/icons/check';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import { Button } from '$lib/components/ui/button';

	export interface PickOption {
		value: string;
		label: string;
		hint?: string;
		mono?: boolean;
	}

	interface Props {
		label: string;
		value: string;
		options: PickOption[];
		heading?: PickOption[];
		placeholder?: string;
		onQuery?: (query: string) => void;
		onChange: (value: string) => void;
	}

	let {
		label,
		value,
		options,
		heading = [],
		placeholder = 'Filter',
		onQuery,
		onChange
	}: Props = $props();

	let open = $state(false);
	let current = $derived([...heading, ...options].find((o) => o.value === value));

	function pick(v: string) {
		onChange(v);
		open = false;
	}
</script>

<Popover.Root bind:open>
	<Popover.Trigger>
		{#snippet child({ props })}
			<Button
				{...props}
				variant="outline"
				class="max-w-64 justify-between text-xs font-normal {value ? '' : 'text-muted-foreground'}"
				aria-label="{placeholder}: {current?.label ?? label}"
			>
				<span class="truncate {current?.mono ? 'font-mono' : ''}">{current?.label ?? label}</span>
				<ChevronDown class="size-3.5 shrink-0 opacity-60" />
			</Button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-72 p-0" align="start">
		<Command.Root>
			<Command.Input
				{placeholder}
				class="h-9 text-xs"
				oninput={(e) => onQuery?.(e.currentTarget.value)}
			/>
			<Command.List class="max-h-64">
				<Command.Empty class="py-4 text-xs">No matches</Command.Empty>
				{#if heading.length}
					<Command.Group>
						{#each heading as option (option.value)}
							<Command.Item
								value="{option.label} {option.hint ?? ''} {option.value}"
								onSelect={() => pick(option.value)}
								class="text-xs"
							>
								<Check class="size-3.5 {value === option.value ? '' : 'opacity-0'}" />
								{option.label}
							</Command.Item>
						{/each}
					</Command.Group>
					<Command.Separator />
				{/if}
				<Command.Group>
					{#each options as option (option.value)}
						<Command.Item
							value="{option.label} {option.hint ?? ''} {option.value}"
							onSelect={() => pick(option.value)}
							class="text-xs"
						>
							<Check class="size-3.5 {value === option.value ? '' : 'opacity-0'}" />
							<span class="min-w-0 flex-1 truncate {option.mono ? 'font-mono' : ''}"
								>{option.label}</span
							>
							{#if option.hint}<span class="text-2xs text-muted-foreground">{option.hint}</span
								>{/if}
						</Command.Item>
					{/each}
				</Command.Group>
			</Command.List>
		</Command.Root>
	</Popover.Content>
</Popover.Root>
