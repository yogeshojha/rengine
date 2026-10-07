<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import type { IconComponent } from '$lib/config/icons';

	export interface PickerItem {
		id: string;
		label: string;
		color?: string;
	}

	interface Props {
		label: string;
		icon: IconComponent;
		items: PickerItem[];
		selected: string[];
		labelOf: (id: string) => string;
		multiple?: boolean;
		loading?: boolean;
		placeholder?: string;
		onSearch?: (q: string) => void;
		onChange: (ids: string[]) => void;
	}

	let {
		label,
		icon: Icon,
		items,
		selected,
		labelOf,
		multiple = false,
		loading = false,
		placeholder = 'Search',
		onSearch,
		onChange
	}: Props = $props();

	let open = $state(false);
	let search = $state('');
	let draft = $state<string[]>([]);

	let visible = $derived(
		onSearch
			? items
			: items.filter((i) => i.label.toLowerCase().includes(search.trim().toLowerCase()))
	);
	let summary = $derived(
		selected.length === 0
			? ''
			: selected.length === 1
				? labelOf(selected[0])
				: `${labelOf(selected[0])} +${selected.length - 1}`
	);

	function openChange(next: boolean) {
		if (next) {
			draft = [...selected];
			search = '';
			onSearch?.('');
		} else if (multiple && !same(draft, selected)) {
			onChange(draft);
		}
		open = next;
	}

	function same(a: string[], b: string[]) {
		return a.length === b.length && a.every((id) => b.includes(id));
	}

	function pick(id: string) {
		if (!multiple) {
			open = false;
			if (!(selected.length === 1 && selected[0] === id)) onChange([id]);
			return;
		}
		draft = draft.includes(id) ? draft.filter((d) => d !== id) : [...draft, id];
	}

	let chosen = $derived(multiple ? draft : selected);
</script>

<div
	class="flex h-8 items-center rounded-md border bg-background text-sm transition-colors {selected.length
		? 'border-primary/40 bg-primary/5'
		: ''}"
>
	<Popover.Root {open} onOpenChange={openChange}>
		<Popover.Trigger>
			{#snippet child({ props })}
				<button
					{...props}
					type="button"
					class="flex h-full max-w-72 items-center gap-1.5 rounded-md px-2.5 hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				>
					<Icon class="size-3.5 shrink-0 text-muted-foreground" />
					<span class="shrink-0 {selected.length ? 'text-muted-foreground' : ''}">{label}</span>
					{#if summary}
						<span class="truncate font-medium">{summary}</span>
					{/if}
					<ChevronDown class="size-3.5 shrink-0 text-muted-foreground" />
				</button>
			{/snippet}
		</Popover.Trigger>
		<Popover.Content class="w-72 p-0" align="start">
			<Command.Root shouldFilter={false}>
				<Command.Input
					{placeholder}
					bind:value={search}
					oninput={() => onSearch?.(search.trim())}
				/>
				<Command.List class="max-h-72">
					<Command.Empty>{loading ? 'Loading' : 'No matches'}</Command.Empty>
					<Command.Group>
						{#each visible as item (item.id)}
							<Command.Item
								value={item.id}
								onSelect={() => pick(item.id)}
								class="flex items-center gap-2"
							>
								<span
									class="flex size-4 shrink-0 items-center justify-center rounded-sm border {chosen.includes(
										item.id
									)
										? 'border-primary bg-primary text-primary-foreground'
										: ''}"
								>
									{#if chosen.includes(item.id)}<Check class="size-3" />{/if}
								</span>
								{#if item.color}
									<span class="size-2 shrink-0 rounded-full" style="background:{item.color}"></span>
								{/if}
								<span class="flex-1 truncate">{item.label}</span>
							</Command.Item>
						{/each}
					</Command.Group>
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>
	{#if selected.length}
		<Button
			variant="ghost"
			size="icon-xs"
			class="mr-1 text-muted-foreground"
			aria-label="Clear {label.toLowerCase()}"
			onclick={() => onChange([])}
		>
			<X class="size-3.5" />
		</Button>
	{/if}
</div>
