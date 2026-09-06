<script lang="ts">
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import * as Select from '$lib/components/ui/select';
	import { Button } from '$lib/components/ui/button';
	import { wordlists as store } from '$lib/stores/wordlists.svelte';
	import { ROUTES } from '$lib/config/routes';

	interface Props {
		id: string;
		kind: string;
		value: string;
		onChange: (value: string) => void;
	}

	let { id, kind, value, onChange }: Props = $props();

	$effect(() => {
		store.fetch();
	});

	let options = $derived(store.byKind(kind));
	let selected = $derived(options.find((w) => w.slug === value) ?? null);
	let label = $derived(
		selected
			? `${selected.name} · ${selected.words.toLocaleString()} words`
			: value
				? `${value} · not in the library`
				: 'Select a wordlist'
	);
</script>

<div class="flex items-center gap-1.5">
	<Select.Root type="single" {value} onValueChange={(v) => v && onChange(v)}>
		<Select.Trigger {id} class="w-[280px]" aria-label="Wordlist">{label}</Select.Trigger>
		<Select.Content>
			{#if options.length}
				{#each options as item (item.id)}
					<Select.Item value={item.slug} label={item.name}>
						<span class="flex w-full items-center justify-between gap-3">
							<span class="truncate">{item.name}</span>
							<span class="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
								{item.words.toLocaleString()}
							</span>
						</span>
					</Select.Item>
				{/each}
			{:else}
				<div class="px-2 py-3 text-sm text-muted-foreground">
					No wordlist of this kind yet. Upload one in the Tools Arsenal.
				</div>
			{/if}
		</Select.Content>
	</Select.Root>
	<Button
		variant="ghost"
		size="icon"
		class="size-8 shrink-0"
		href={ROUTES.arsenal('wordlists')}
		target="_blank"
		rel="noreferrer"
		aria-label="Manage wordlists in the Tools Arsenal"
	>
		<ExternalLink class="size-3.5" />
	</Button>
</div>
