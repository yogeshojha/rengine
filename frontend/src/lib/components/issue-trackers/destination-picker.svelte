<script lang="ts">
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import CheckIcon from '@lucide/svelte/icons/check';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import { issueTrackersApi } from '$lib/api/issue-trackers';
	import type { TrackerOption } from '$lib/types/issue-tracker';

	interface Props {
		trackerId: string | null;
		value: string;
		placeholder?: string;
		kind?: 'destination' | 'issue-type';
		destination?: string;
		clearable?: boolean;
		searchLabel?: string;
		id?: string;
	}

	let {
		trackerId,
		value = $bindable(),
		placeholder = '',
		kind = 'destination',
		destination = '',
		clearable = false,
		searchLabel = 'Search',
		id
	}: Props = $props();

	const SEARCH_DELAY_MS = 250;

	let open = $state(false);
	let search = $state('');
	let options = $state<TrackerOption[]>([]);
	let loading = $state(false);
	let failure = $state<string | null>(null);
	let req = 0;

	const typed = $derived(search.trim());
	const offerTyped = $derived(typed !== '' && !options.some((o) => o.key === typed));
	const current = $derived(options.find((o) => o.key === value));

	async function fetchOptions(q: string) {
		if (!trackerId) return;
		const my = ++req;
		loading = true;
		failure = null;
		try {
			const rows =
				kind === 'issue-type'
					? destination
						? await issueTrackersApi.issueTypes(trackerId, destination)
						: []
					: await issueTrackersApi.destinations(trackerId, q);
			if (my === req) options = rows;
		} catch (e) {
			if (my === req) failure = e instanceof Error ? e.message : 'Options not loaded';
		} finally {
			if (my === req) loading = false;
		}
	}

	$effect(() => {
		void [trackerId, destination, kind];
		req += 1;
		options = [];
		failure = null;
		loading = false;
	});

	$effect(() => {
		if (!open) return;
		void [trackerId, destination];
		const q = kind === 'issue-type' ? '' : search;
		const timer = setTimeout(() => void fetchOptions(q), SEARCH_DELAY_MS);
		return () => clearTimeout(timer);
	});

	function pick(key: string) {
		value = key;
		open = false;
		search = '';
	}
</script>

{#if !trackerId}
	<Input {id} bind:value {placeholder} />
{:else}
	<Popover.Root bind:open>
		<Popover.Trigger class="w-full">
			{#snippet child({ props })}
				<Button
					{...props}
					{id}
					variant="outline"
					role="combobox"
					class="h-9 w-full justify-between font-normal"
				>
					<span class="min-w-0 truncate {value ? 'font-mono' : 'text-muted-foreground'}">
						{value || placeholder}
						{#if current && current.name !== current.key}
							<span class="ml-1 font-sans text-muted-foreground">{current.name}</span>
						{/if}
					</span>
					<ChevronsUpDownIcon class="size-4 shrink-0 text-muted-foreground" />
				</Button>
			{/snippet}
		</Popover.Trigger>
		<Popover.Content class="w-(--bits-popover-anchor-width) p-0" align="start">
			<Command.Root shouldFilter={kind === 'issue-type'}>
				<Command.Input placeholder={searchLabel} bind:value={search} />
				<Command.List class="max-h-none overflow-visible">
					{#if loading && !options.length}
						<div class="flex items-center gap-2 px-3 py-3 text-sm text-muted-foreground">
							<Spinner class="size-4" />
						</div>
					{:else if failure}
						<div class="px-3 py-3 text-sm text-destructive">{failure}</div>
					{:else}
						<Command.Empty>No matches</Command.Empty>
					{/if}
					<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
						<Command.Group>
							{#each options as option (option.key)}
								<Command.Item value={option.key} onSelect={() => pick(option.key)}>
									<span class="min-w-0 flex-1 truncate">
										<span class="font-mono">{option.key}</span>
										{#if option.name !== option.key}
											<span class="ml-1 text-muted-foreground">{option.name}</span>
										{/if}
									</span>
									{#if option.key === value}
										<CheckIcon class="size-4 text-primary" />
									{/if}
								</Command.Item>
							{/each}
						</Command.Group>
					</ScrollArea>
					{#if clearable && value}
						<Command.Group>
							<Command.Item value="__none__ none" onSelect={() => pick('')}>
								<span class="text-muted-foreground">None</span>
							</Command.Item>
						</Command.Group>
					{/if}
					{#if offerTyped}
						<Command.Group>
							<Command.Item value={`use ${typed}`} onSelect={() => pick(typed)}>
								Use <span class="font-mono">{typed}</span>
							</Command.Item>
						</Command.Group>
					{/if}
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>
{/if}
