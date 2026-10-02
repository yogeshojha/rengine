<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Hint from '$lib/components/hint.svelte';
	import { ai } from '$lib/stores/ai.svelte';
	import { formatRate } from '$lib/config/ai';
	import type { AiModelOption, AiModelsRequest } from '$lib/types/ai';

	interface Props {
		provider: string;
		value: string;
		selected?: AiModelOption | null;
		request: AiModelsRequest | null;
		id?: string;
		placeholder?: string;
		disabled?: boolean;
		loading?: boolean;
	}

	let {
		provider,
		value = $bindable(),
		selected = $bindable(null),
		request,
		id,
		placeholder = 'Choose a model',
		disabled = false,
		loading = $bindable(false)
	}: Props = $props();

	const DEBOUNCE_MS = 500;
	const PRICE_COL = 'w-16 shrink-0 text-right tabular-nums';

	let open = $state(false);
	let search = $state('');
	let listed = $state<{ provider: string; models: AiModelOption[] } | null>(null);
	let error = $state<string | null>(null);
	let seq = 0;
	let mounted = false;

	const requestKey = $derived(request ? JSON.stringify(request) : '');
	const curated = $derived<AiModelOption[]>(
		(ai.provider(provider)?.models ?? []).map((m) => ({
			id: m.id,
			label: m.label,
			input_per_mtok: m.input_per_mtok,
			output_per_mtok: m.output_per_mtok,
			cache_read_per_mtok: m.cache_read_per_mtok,
			cache_write_per_mtok: m.cache_write_per_mtok,
			recommended: m.recommended
		}))
	);
	const options = $derived(listed?.provider === provider ? listed.models : curated);
	const query = $derived(search.trim().toLowerCase());
	const visible = $derived(
		query
			? options.filter(
					(m) => m.id.toLowerCase().includes(query) || m.label.toLowerCase().includes(query)
				)
			: options
	);
	const recommended = $derived(visible.filter((m) => m.recommended));
	const others = $derived(visible.filter((m) => !m.recommended));
	const current = $derived(options.find((m) => m.id === value) ?? null);
	const typed = $derived(search.trim());
	const offerTyped = $derived(typed !== '' && !options.some((m) => m.id === typed));
	const priced = $derived(
		options.some((m) => m.input_per_mtok !== null || m.output_per_mtok !== null)
	);

	$effect.pre(() => {
		selected = current;
	});

	async function load(force = false) {
		const body = request;
		if (!body) return;
		const mine = ++seq;
		const owner = provider;
		loading = true;
		error = null;
		try {
			const result = await ai.listModels(body, force);
			if (mine !== seq) return;
			listed = result.error ? null : { provider: owner, models: result.models };
			error = result.error;
		} catch (e) {
			if (mine !== seq) return;
			listed = null;
			error = e instanceof Error ? e.message : 'Models not loaded';
		} finally {
			if (mine === seq) loading = false;
		}
	}

	$effect(() => {
		const key = requestKey;
		const delay = mounted ? DEBOUNCE_MS : 0;
		mounted = true;
		seq += 1;
		loading = false;
		if (!key) {
			listed = null;
			error = null;
			return;
		}
		const timer = setTimeout(() => void load(), delay);
		return () => clearTimeout(timer);
	});

	function pick(model: string) {
		value = model;
		open = false;
		search = '';
	}
</script>

{#snippet option(m: AiModelOption)}
	<Command.Item value={m.id} onSelect={() => pick(m.id)}>
		<CheckIcon class="size-4 {m.id === value ? 'text-primary' : 'text-transparent'}" />
		<span class="flex min-w-0 flex-1 flex-col">
			<span class="font-mono text-xs wrap-anywhere">{m.id}</span>
			{#if m.label !== m.id}
				<span class="text-2xs text-muted-foreground">{m.label}</span>
			{/if}
		</span>
		{#if priced}
			<span class="{PRICE_COL} text-xs">
				{#if m.input_per_mtok !== null}<span class="sr-only">Input</span>{/if}
				{formatRate(m.input_per_mtok)}
			</span>
			<span class="{PRICE_COL} text-xs">
				{#if m.output_per_mtok !== null}<span class="sr-only">Output</span>{/if}
				{formatRate(m.output_per_mtok)}
			</span>
		{/if}
	</Command.Item>
{/snippet}

<div class="flex min-w-0 flex-col gap-1.5">
	<div class="flex min-w-0 items-center gap-2">
		<Popover.Root
			bind:open
			onOpenChange={(next) => {
				if (!next) search = '';
			}}
		>
			<Popover.Trigger class="min-w-0 flex-1" {disabled}>
				{#snippet child({ props })}
					<Button
						{...props}
						{id}
						variant="outline"
						role="combobox"
						aria-expanded={open}
						class="h-9 w-full min-w-0 flex-1 justify-between font-normal"
					>
						<span class="min-w-0 truncate text-left">
							{#if value}
								<span class="font-mono text-xs">{value}</span>
								{#if current && current.label !== current.id}
									<span class="ml-1.5 text-muted-foreground">{current.label}</span>
								{/if}
							{:else}
								<span class="text-muted-foreground">{placeholder}</span>
							{/if}
						</span>
						<ChevronsUpDownIcon class="size-4 shrink-0 text-muted-foreground" />
					</Button>
				{/snippet}
			</Popover.Trigger>
			<Popover.Content class="w-(--bits-popover-anchor-width) min-w-80 p-0" align="start">
				<Command.Root shouldFilter={false}>
					<Command.Input placeholder="Search models" bind:value={search} />
					{#if priced && visible.length}
						<div
							class="flex items-end gap-2 border-b px-3 pt-2 pb-1.5 text-xs font-medium text-muted-foreground"
							aria-hidden="true"
						>
							<span class="size-4 shrink-0"></span>
							<span class="min-w-0 flex-1">Model</span>
							<span class="flex shrink-0 flex-col items-end gap-0.5">
								<span class="text-2xs font-normal">per 1M tokens</span>
								<span class="flex gap-2">
									<span class={PRICE_COL}>Input</span>
									<span class={PRICE_COL}>Output</span>
								</span>
							</span>
						</div>
					{/if}
					<Command.List class="max-h-none overflow-visible">
						{#if loading && !options.length}
							<div class="flex flex-col gap-1.5 p-2">
								<Skeleton class="h-8 w-full" />
								<Skeleton class="h-8 w-full" />
								<Skeleton class="h-8 w-full" />
							</div>
						{:else}
							<Command.Empty>No models</Command.Empty>
						{/if}
						<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
							{#if recommended.length}
								<Command.Group heading="Recommended">
									{#each recommended as m (m.id)}
										{@render option(m)}
									{/each}
								</Command.Group>
							{/if}
							{#if others.length}
								<Command.Group heading={recommended.length ? 'All models' : undefined}>
									{#each others as m (m.id)}
										{@render option(m)}
									{/each}
								</Command.Group>
							{/if}
						</ScrollArea>
						{#if offerTyped}
							<Command.Group>
								<Command.Item value={`use ${typed}`} onSelect={() => pick(typed)}>
									<CheckIcon class="size-4 text-transparent" />
									Use <span class="font-mono text-xs">{typed}</span>
								</Command.Item>
							</Command.Group>
						{/if}
					</Command.List>
				</Command.Root>
			</Popover.Content>
		</Popover.Root>
		<Hint text="Reload models">
			{#snippet child(props)}
				<Button
					{...props}
					variant="outline"
					size="icon"
					class="size-9 shrink-0"
					aria-label="Reload models"
					disabled={disabled || !request || loading}
					onclick={() => load(true)}
				>
					{#if loading}
						<Spinner class="size-4" />
					{:else}
						<RotateCwIcon class="size-4" />
					{/if}
				</Button>
			{/snippet}
		</Hint>
	</div>
	{#if error}
		<p class="text-xs text-destructive wrap-anywhere">{error}</p>
	{/if}
</div>
