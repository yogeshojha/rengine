<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import * as InputGroup from '$lib/components/ui/input-group';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import { cn } from '$lib/utils';
	import type { DslKey, Facet } from '$lib/utilities/scan-insights';

	interface Props {
		value: string;
		keys: DslKey[];
		values: object;
		placeholder: string;
		onChange: (value: string) => void;
		ref?: HTMLInputElement | null;
		class?: string;
	}

	let {
		value,
		keys,
		values,
		placeholder,
		onChange,
		ref = $bindable(null),
		class: className
	}: Props = $props();

	interface Suggestion {
		insert: string;
		label: string;
		hint?: string;
	}

	const MAX = 8;

	let inputFocused = $state(false);
	let listFocused = $state(false);
	let dismissed = $state(false);
	let anchor = $state<HTMLElement | null>(null);
	let listEl = $state<HTMLElement | null>(null);

	let tail = $derived(value.split(/\s+/).pop() ?? '');
	let head = $derived(value.slice(0, value.length - tail.length));
	let suggestions = $derived.by<Suggestion[]>(() => {
		const i = tail.indexOf(':');
		if (i > 0) {
			const key = tail.slice(0, i).toLowerCase();
			const partial = tail.slice(i + 1).toLowerCase();
			const def = keys.find((k) => k.key === key);
			if (!def) return [];
			const lookup = values as Record<string, Facet[] | undefined>;
			const options: Facet[] = def.values
				? def.values.map((v) => ({ value: v, label: v, count: 0 }))
				: def.facet
					? (lookup[def.facet] ?? [])
					: [];
			return options
				.filter(
					(o) =>
						(o.value.toLowerCase().startsWith(partial) ||
							o.label.toLowerCase().includes(partial)) &&
						o.value.toLowerCase() !== partial
				)
				.slice(0, MAX)
				.map((o) => ({
					insert: `${key}:${o.value} `,
					label: `${key}:${o.value}`,
					hint: o.label !== o.value ? o.label : undefined
				}));
		}
		const p = tail.toLowerCase();
		return keys
			.filter((k) => k.key.startsWith(p))
			.slice(0, MAX)
			.map((k) => ({ insert: `${k.key}:`, label: `${k.key}:`, hint: k.hint }));
	});
	let open = $derived((inputFocused || listFocused) && !dismissed && suggestions.length > 0);

	function apply(s: Suggestion) {
		onChange(head + s.insert);
		dismissed = false;
		ref?.focus();
	}
	function buttons(): HTMLElement[] {
		return [...(listEl?.querySelectorAll('button') ?? [])] as HTMLElement[];
	}
	function onInputKey(e: KeyboardEvent) {
		if (e.key === 'ArrowDown' && open) {
			e.preventDefault();
			buttons()[0]?.focus();
		} else if (e.key === 'Escape') {
			if (open) {
				e.preventDefault();
				dismissed = true;
			} else if (value) onChange('');
		}
	}
	function onListKey(e: KeyboardEvent) {
		const btns = buttons();
		const i = btns.indexOf(document.activeElement as HTMLElement);
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			btns[Math.min(i + 1, btns.length - 1)]?.focus();
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (i <= 0) ref?.focus();
			else btns[i - 1]?.focus();
		} else if (e.key === 'Escape') {
			e.preventDefault();
			dismissed = true;
			ref?.focus();
		}
	}
</script>

<div bind:this={anchor} class="w-full">
	<InputGroup.Root class={cn('h-9 bg-background', className)}>
		<InputGroup.Addon>
			<Search />
		</InputGroup.Addon>
		<InputGroup.Input
			bind:ref
			{value}
			oninput={(e) => {
				dismissed = false;
				onChange(e.currentTarget.value);
			}}
			onfocus={() => {
				inputFocused = true;
				dismissed = false;
			}}
			onblur={() => (inputFocused = false)}
			onkeydown={onInputKey}
			{placeholder}
			class="font-mono text-sm"
			aria-label="Search"
			autocomplete="off"
			spellcheck={false}
		/>
		<InputGroup.Addon align="inline-end">
			{#if value}
				<InputGroup.Button size="icon-xs" onclick={() => onChange('')} aria-label="Clear search">
					<X />
				</InputGroup.Button>
			{:else}
				<Kbd>/</Kbd>
			{/if}
		</InputGroup.Addon>
	</InputGroup.Root>
</div>

<Popover.Root
	{open}
	onOpenChange={(o) => {
		if (!o) dismissed = true;
	}}
>
	<Popover.Content
		customAnchor={anchor}
		align="start"
		sideOffset={6}
		trapFocus={false}
		onOpenAutoFocus={(e) => e.preventDefault()}
		onCloseAutoFocus={(e) => e.preventDefault()}
		class="w-(--bits-popover-anchor-width) p-1"
	>
		<div
			bind:this={listEl}
			role="listbox"
			tabindex={-1}
			aria-label="Search suggestions"
			onkeydown={onListKey}
			onmousedown={(e) => e.preventDefault()}
			onfocusin={() => (listFocused = true)}
			onfocusout={(e) => (listFocused = !!listEl?.contains(e.relatedTarget as Node | null))}
		>
			{#each suggestions as s (s.insert)}
				<Button
					variant="ghost"
					size="sm"
					class="w-full justify-start gap-3 font-normal"
					onclick={() => apply(s)}
				>
					<span class="font-mono text-xs">{s.label}</span>
					{#if s.hint}<span class="truncate text-xs text-muted-foreground">{s.hint}</span>{/if}
				</Button>
			{/each}
		</div>
	</Popover.Content>
</Popover.Root>
