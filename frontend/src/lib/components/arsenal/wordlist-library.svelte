<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Eye from '@lucide/svelte/icons/eye';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Upload from '@lucide/svelte/icons/upload';
	import * as Card from '$lib/components/ui/card';
	import * as Select from '$lib/components/ui/select';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import WordlistSheet from './wordlist-sheet.svelte';
	import { wordlists as store } from '$lib/stores/wordlists.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		WORDLIST_KINDS,
		WORDLIST_KIND_LABELS,
		type Wordlist,
		type WordlistKind
	} from '$lib/types/wordlist';

	const ALL = 'all';

	let kindFilter = $state<string>(ALL);
	let uploadKind = $state<WordlistKind>('subdomain');
	let uploading = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);
	let removing = $state<Wordlist | null>(null);
	let viewing = $state<Wordlist | null>(null);

	$effect(() => {
		store.fetch();
	});

	let items = $derived(
		kindFilter === ALL ? store.wordlists : store.wordlists.filter((w) => w.kind === kindFilter)
	);
	let counts = $derived(
		Object.fromEntries(
			WORDLIST_KINDS.map((k) => [k, store.wordlists.filter((w) => w.kind === k).length])
		) as Record<WordlistKind, number>
	);

	function size(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	async function upload(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const chosen = Array.from(input.files ?? []);
		input.value = '';
		if (!chosen.length) return;
		uploading = true;
		try {
			const files = await Promise.all(
				chosen.map(async (file) => ({
					filename: file.name,
					content: await file.text(),
					name: file.name.replace(/\.[^.]+$/, '')
				}))
			);
			const result = await store.upload({ kind: uploadKind, files });
			if (!result) return;
			if (result.stored.length) {
				const words = result.stored.reduce((sum, w) => sum + w.words, 0);
				toast.success(
					`${result.stored.length} ${result.stored.length === 1 ? 'wordlist' : 'wordlists'} added`,
					{ description: `${words.toLocaleString()} words are now selectable in a scan engine.` }
				);
			}
			for (const rejection of result.rejected) {
				toast.error(`${rejection.filename} was not added`, { description: rejection.reason });
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Upload failed');
		} finally {
			uploading = false;
		}
	}

	async function remove() {
		const target = removing;
		if (!target) return;
		if (await store.remove(target.id)) toast.success(`${target.name} removed`);
		removing = null;
	}
</script>

<div class="space-y-6">
	<Card.Root class="gap-0 py-0">
		<Card.Header class="border-b py-5">
			<Card.Title>Wordlists</Card.Title>
			<Card.Description>
				Wordlists a scan draws from. Shipped lists come with reNgine; uploaded lists sit beside them
				and are selected by name in a scan engine.
			</Card.Description>
			<Card.Action class="flex items-center gap-2">
				<Select.Root type="single" bind:value={uploadKind}>
					<Select.Trigger class="w-[190px]" aria-label="What the words are">
						{WORDLIST_KIND_LABELS[uploadKind]}
					</Select.Trigger>
					<Select.Content>
						{#each WORDLIST_KINDS as kind (kind)}
							<Select.Item value={kind}>{WORDLIST_KIND_LABELS[kind]}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
				<input
					bind:this={fileInput}
					type="file"
					accept=".txt,.lst,.list,text/plain"
					multiple
					class="hidden"
					onchange={upload}
				/>
				<LoadingButton
					size="sm"
					class="gap-2"
					loading={uploading}
					loadingLabel="Uploading…"
					onclick={() => fileInput?.click()}
				>
					<Upload class="size-4" /> Upload wordlist
				</LoadingButton>
			</Card.Action>
		</Card.Header>

		<Card.Content class="p-0">
			<div class="border-b px-6 py-3">
				<ToggleGroup.Root
					type="single"
					variant="outline"
					size="sm"
					spacing={1}
					value={kindFilter}
					onValueChange={(v) => (kindFilter = v || ALL)}
					class="flex-wrap justify-start"
					aria-label="Filter by what the words are"
				>
					<ToggleGroup.Item value={ALL}>All {store.wordlists.length}</ToggleGroup.Item>
					{#each WORDLIST_KINDS as kind (kind)}
						<ToggleGroup.Item value={kind}>
							{WORDLIST_KIND_LABELS[kind]}
							{counts[kind]}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
			</div>

			{#if store.isLoading && !store.hasFetched}
				<div class="space-y-3 p-6">
					<Skeleton class="h-12 w-full" />
					<Skeleton class="h-12 w-full" />
				</div>
			{:else if !items.length}
				<div class="p-6">
					<EmptyState
						icon={Upload}
						title="No wordlists yet"
						description="Upload a text file with one word per line. It becomes selectable in every scan engine."
					/>
				</div>
			{:else}
				{#each items as item (item.id)}
					<div class="flex items-start gap-4 border-b px-6 py-4 last:border-b-0 hover:bg-muted/40">
						<div class="min-w-0 flex-1 space-y-1">
							<div class="flex flex-wrap items-center gap-2">
								<span class="font-medium">{item.name}</span>
								<Badge variant={item.origin === 'builtin' ? 'secondary' : 'info'}>
									{item.origin === 'builtin' ? 'Shipped' : 'Uploaded'}
								</Badge>
								<Badge variant="outline">{WORDLIST_KIND_LABELS[item.kind]}</Badge>
							</div>
							{#if item.description}
								<p class="text-sm text-muted-foreground">{item.description}</p>
							{/if}
							<Hint text="The name a scan engine refers to this list by">
								{#snippet child(props)}
									<code
										{...props}
										class="inline-block rounded border bg-muted/60 px-1.5 py-0.5 font-mono text-xs text-muted-foreground"
										>{item.slug}</code
									>
								{/snippet}
							</Hint>
						</div>

						<div class="shrink-0 text-right font-mono text-xs tabular-nums text-muted-foreground">
							<div class="text-sm text-foreground">{item.words.toLocaleString()} words</div>
							<div>{size(item.bytes)}</div>
							<div>{relativeTime(item.updated_at)}</div>
						</div>

						<div class="flex shrink-0 items-center gap-1">
							<Hint text="Preview the first words">
								{#snippet child(props)}
									<Button
										{...props}
										variant="ghost"
										size="icon"
										class="size-8"
										onclick={() => (viewing = item)}
									>
										<Eye class="size-4" />
									</Button>
								{/snippet}
							</Hint>
							<Hint text={item.origin === 'builtin' ? 'Shipped lists cannot be removed' : 'Remove'}>
								{#snippet child(props)}
									<span class="inline-flex">
										<Button
											{...props}
											variant="ghost"
											size="icon"
											class="size-8"
											disabled={item.origin === 'builtin'}
											onclick={() => (removing = item)}
										>
											<Trash2 class="size-4" />
										</Button>
									</span>
								{/snippet}
							</Hint>
						</div>
					</div>
				{/each}
			{/if}
		</Card.Content>
	</Card.Root>
</div>

<WordlistSheet
	wordlist={viewing}
	onOpenChange={(open) => {
		if (!open) viewing = null;
	}}
/>

<DeleteConfirmationDialog
	open={!!removing}
	onOpenChange={(value) => {
		if (!value) removing = null;
	}}
	title="Remove this wordlist?"
	description="The list is removed from the library and its file deleted. A scan engine still referencing it reports the list as missing."
	confirmLabel="Remove"
	onConfirm={remove}
/>
