<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import * as Popover from '$lib/components/ui/popover';
	import { Spinner } from '$lib/components/ui/spinner';
	import { targetsApi } from '$lib/api/targets';
	import type { Target } from '$lib/types/target';
	import { targetTypeLabel } from '$lib/types/scan-engine';
	import {
		chipFor,
		INVALID_TARGET_MESSAGE,
		resolveTargetValue,
		splitTargetInput,
		TARGET_FORMATS
	} from './targets';
	import type { TargetChip } from './launch-state.svelte';

	interface Props {
		chips: TargetChip[];
		projectSlug: string;
		disabled?: boolean;
		loading?: boolean;
		onAdd: (chip: TargetChip) => void;
		onRemove: (key: string) => void;
	}

	let { chips, projectSlug, disabled = false, loading = false, onAdd, onRemove }: Props = $props();

	const SEARCH_DEBOUNCE_MS = 200;
	const MIN_QUERY = 2;

	let query = $state('');
	let inputEl = $state<HTMLInputElement | null>(null);
	let suggestions = $state<Target[]>([]);
	let searching = $state(false);
	let adding = $state(false);
	let highlight = $state(-1);
	let error = $state<string | null>(null);

	let trimmed = $derived(query.trim());
	let visible = $derived(suggestions.filter((t) => !chips.some((c) => c.id === t.id)));
	let open = $derived(trimmed.length >= MIN_QUERY && (visible.length > 0 || searching));

	$effect(() => {
		const q = trimmed;
		highlight = -1;
		if (q.length < MIN_QUERY) {
			suggestions = [];
			searching = false;
			return;
		}
		searching = true;
		const timer = setTimeout(async () => {
			try {
				suggestions = await targetsApi.searchByValue(q, projectSlug);
			} catch {
				suggestions = [];
			} finally {
				searching = false;
			}
		}, SEARCH_DEBOUNCE_MS);
		return () => clearTimeout(timer);
	});

	function pick(target: Target) {
		onAdd(chipFor(target));
		query = '';
		error = null;
	}

	async function commitTyped() {
		const values = splitTargetInput(query);
		if (values.length === 0) return;
		adding = true;
		error = null;
		const rejected: string[] = [];
		try {
			for (const value of values) {
				const exact = visible.find((t) => t.target_value.toLowerCase() === value.toLowerCase());
				if (exact) {
					onAdd(chipFor(exact));
					continue;
				}
				const chip = await resolveTargetValue(value, projectSlug);
				if (chip) onAdd(chip);
				else rejected.push(value);
			}
		} finally {
			adding = false;
		}
		query = rejected.join(' ');
		error = rejected.length
			? `${INVALID_TARGET_MESSAGE}: ${rejected.join(', ')}. ${TARGET_FORMATS}`
			: null;
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			if (highlight >= 0 && visible[highlight]) {
				e.preventDefault();
				e.stopPropagation();
				pick(visible[highlight]);
				return;
			}
			if (trimmed) {
				e.preventDefault();
				e.stopPropagation();
				commitTyped();
			}
			return;
		}
		if (e.key === ',' || e.key === ' ') {
			if (trimmed) {
				e.preventDefault();
				commitTyped();
			}
			return;
		}
		if (e.key === 'ArrowDown' && visible.length) {
			e.preventDefault();
			highlight = (highlight + 1) % visible.length;
		} else if (e.key === 'ArrowUp' && visible.length) {
			e.preventDefault();
			highlight = highlight <= 0 ? visible.length - 1 : highlight - 1;
		} else if (e.key === 'Backspace' && !query && chips.length) {
			onRemove(chips[chips.length - 1].key);
		} else if (e.key === 'Escape' && query) {
			e.stopPropagation();
			query = '';
		}
	}

	function onPaste(e: ClipboardEvent) {
		const text = e.clipboardData?.getData('text') ?? '';
		if (!/[\s,;]/.test(text.trim())) return;
		e.preventDefault();
		query = `${query} ${text}`.trim();
		commitTyped();
	}
</script>

<div class="flex flex-col gap-1.5">
	<Popover.Root {open}>
		<Popover.Trigger>
			{#snippet child({ props })}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					{...props}
					class="flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-2 py-1 text-sm shadow-xs transition-[color,box-shadow] focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/50 {error
						? 'border-destructive'
						: ''}"
					onclick={() => inputEl?.focus()}
					onkeydown={(e) => e.key === 'Enter' && e.stopPropagation()}
				>
					{#if chips.length === 0}
						<Search class="ml-1 size-4 shrink-0 text-muted-foreground" />
					{/if}
					{#each chips as chip (chip.key)}
						<span
							class="inline-flex h-6 items-center gap-1 rounded-sm bg-muted pr-0.5 pl-2 text-secondary-foreground"
						>
							<span class="font-mono text-xs">{chip.value}</span>
							{#if !chip.id}
								<span
									class="rounded-full border border-border bg-background px-1.5 text-[10px] leading-4 text-muted-foreground"
								>
									New
								</span>
							{/if}
							<button
								type="button"
								class="rounded-sm p-0.5 text-muted-foreground hover:bg-foreground/10 hover:text-foreground"
								aria-label="Remove {chip.value}"
								{disabled}
								onclick={(e) => {
									e.stopPropagation();
									onRemove(chip.key);
								}}
							>
								<X class="size-3" />
							</button>
						</span>
					{/each}
					<input
						bind:this={inputEl}
						bind:value={query}
						class="h-6 min-w-40 flex-1 bg-transparent outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
						placeholder={chips.length
							? 'Add another target'
							: 'Domain, IP address, CIDR range, URL or ASN'}
						autocomplete="off"
						spellcheck="false"
						disabled={disabled || loading}
						onkeydown={onKeydown}
						onpaste={onPaste}
					/>
					{#if adding || loading}
						<Spinner class="size-3.5 text-muted-foreground" />
					{/if}
				</div>
			{/snippet}
		</Popover.Trigger>
		<Popover.Content
			class="w-(--bits-popover-anchor-width) p-1"
			align="start"
			sideOffset={4}
			trapFocus={false}
			onOpenAutoFocus={(e) => e.preventDefault()}
			onCloseAutoFocus={(e) => e.preventDefault()}
			interactOutsideBehavior="ignore"
		>
			{#if visible.length === 0}
				<div class="flex items-center gap-2 px-2 py-1.5 text-xs text-muted-foreground">
					<Spinner class="size-3" /> Searching targets…
				</div>
			{:else}
				<ul role="listbox" aria-label="Matching targets">
					{#each visible as target, i (target.id)}
						<li>
							<button
								type="button"
								role="option"
								aria-selected={i === highlight}
								class="flex h-8 w-full items-center gap-2 rounded-sm px-2 text-left text-sm hover:bg-accent {i ===
								highlight
									? 'bg-accent'
									: ''}"
								onmousedown={(e) => e.preventDefault()}
								onclick={() => pick(target)}
							>
								<span class="min-w-0 flex-1 truncate font-mono text-xs">{target.target_value}</span>
								<span class="text-[11px] text-muted-foreground">
									{targetTypeLabel(target.target_type)}
								</span>
							</button>
						</li>
					{/each}
					{#if trimmed && !visible.some((t) => t.target_value.toLowerCase() === trimmed.toLowerCase())}
						<li>
							<button
								type="button"
								class="flex h-8 w-full items-center gap-2 rounded-sm px-2 text-left text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
								onmousedown={(e) => e.preventDefault()}
								onclick={commitTyped}
							>
								<Plus class="size-3.5" />
								<span class="truncate">Add <span class="font-mono text-xs">{trimmed}</span></span>
							</button>
						</li>
					{/if}
				</ul>
			{/if}
		</Popover.Content>
	</Popover.Root>
	{#if error}
		<p class="text-[11px] text-destructive">{error}</p>
	{:else if chips.length > 1}
		<p class="text-[11px] text-muted-foreground">Each target runs as its own scan.</p>
	{/if}
</div>
