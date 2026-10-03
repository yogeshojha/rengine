<script lang="ts">
	import { untrack } from 'svelte';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import * as Select from '$lib/components/ui/select';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
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
		untrack(() => store.fetch());
	});

	let failed = $derived(!store.hasFetched && store.error !== null);
	let options = $derived(store.byKind(kind));
	let selected = $derived(options.find((w) => w.slug === value) ?? null);
	let label = $derived(
		selected
			? `${selected.name} · ${selected.words.toLocaleString()} words`
			: value
				? store.hasFetched
					? `${value} · not in the library`
					: value
				: 'Select a wordlist'
	);
</script>

<div class="flex max-w-full flex-col items-end gap-1.5">
	<div class="flex max-w-full items-center gap-1.5">
		<Select.Root type="single" {value} onValueChange={(v) => v && onChange(v)}>
			<Select.Trigger {id} class="w-[280px] min-w-0" aria-label="Wordlist">{label}</Select.Trigger>
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
				{:else if failed}
					<div class="px-2 py-3 text-sm text-destructive">Wordlists not loaded.</div>
				{:else}
					<div class="px-2 py-3 text-sm text-muted-foreground">No wordlists of this kind.</div>
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
			aria-label="Open wordlists in Arsenal"
		>
			<ExternalLink class="size-3.5" />
		</Button>
	</div>
	{#if failed}
		<div class="flex items-center gap-3">
			<span class="text-xs text-destructive">Wordlists not loaded.</span>
			<LoadingButton
				variant="outline"
				size="sm"
				class="h-7 text-xs"
				loading={store.isLoading}
				loadingLabel="Retrying"
				onclick={() => store.fetch(true)}
			>
				Retry
			</LoadingButton>
		</div>
	{/if}
</div>
