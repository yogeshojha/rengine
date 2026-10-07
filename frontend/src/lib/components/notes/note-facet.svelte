<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import * as Command from '$lib/components/ui/command';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { cn } from '$lib/utils';
	import type { FacetOption } from './facets';

	interface Props {
		title: string;
		options: FacetOption[];
		selected: string[];
		onChange: (next: string[]) => void;
		onSearch?: (query: string) => void;
	}

	let { title, options, selected, onChange, onSearch }: Props = $props();

	let open = $state(false);
	let query = $state('');
	let timer: ReturnType<typeof setTimeout> | undefined;

	let shown = $derived.by(() => {
		const term = query.trim().toLowerCase();
		if (onSearch || !term) return options;
		return options.filter(
			(o) => o.label.toLowerCase().includes(term) || o.value.toLowerCase().includes(term)
		);
	});

	function search() {
		if (!onSearch) return;
		clearTimeout(timer);
		timer = setTimeout(() => onSearch?.(query.trim()), SEARCH_DEBOUNCE_MS);
	}

	function onOpenChange(next: boolean) {
		open = next;
		if (!next && query) {
			clearTimeout(timer);
			query = '';
			onSearch?.('');
		}
	}

	function toggle(value: string) {
		onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
	}
</script>

<Popover.Root {open} {onOpenChange}>
	<Popover.Trigger>
		{#snippet child({ props })}
			<Button
				{...props}
				variant="outline"
				class={selected.length ? 'border-primary/50 bg-primary/5' : ''}
				disabled={!options.length && !selected.length && !query}
			>
				{title}
				{#if selected.length}
					<Badge variant="secondary" class="h-5 px-1.5 text-xs">{selected.length}</Badge>
				{/if}
				<ChevronDown class="size-3.5 text-muted-foreground" />
			</Button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-72 p-0" align="start">
		<Command.Root shouldFilter={false}>
			<Command.Input placeholder={title} bind:value={query} oninput={search} />
			<Command.List class="max-h-72">
				<Command.Empty>No matches</Command.Empty>
				<Command.Group>
					{#each shown as option (option.value)}
						{@const on = selected.includes(option.value)}
						{@const Icon = option.icon}
						<Command.Item value={option.value} onSelect={() => toggle(option.value)}>
							<span
								class={cn(
									'flex size-4 shrink-0 items-center justify-center rounded-sm border',
									on
										? 'border-primary bg-primary text-primary-foreground'
										: 'border-muted-foreground/40 [&_svg]:invisible'
								)}
							>
								<Check class="size-3" />
							</span>
							{#if Icon}
								<Icon class="size-3.5 shrink-0 text-muted-foreground" />
							{/if}
							<span
								class={cn(
									'line-clamp-2 min-w-0 flex-1 wrap-anywhere',
									option.mono && 'font-mono text-xs'
								)}
							>
								{option.label}
							</span>
							<span class="shrink-0 font-mono text-xs text-muted-foreground tabular-nums">
								{option.count.toLocaleString()}
							</span>
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
