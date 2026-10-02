<script lang="ts">
	import { untrack } from 'svelte';
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
	import SelectionDeleteBar from '$lib/components/selection-delete-bar.svelte';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { SvelteSet } from 'svelte/reactivity';
	import WordlistSheet from './wordlist-sheet.svelte';
	import { wordlists as store } from '$lib/stores/wordlists.svelte';
	import { wordlistsApi } from '$lib/api/wordlists';
	import { relativeTime } from '$lib/utilities/dates';
	import { formatBytes } from '$lib/utilities/format';
	import {
		MAX_WORDLIST_UPLOAD,
		WORDLIST_KINDS,
		WORDLIST_KIND_LABELS,
		WORDLIST_ORIGIN_BADGE,
		WORDLIST_ORIGIN_LABELS,
		WordlistOrigin,
		type Wordlist,
		type WordlistKind
	} from '$lib/types/wordlist';

	const ALL = 'all';

	let kindFilter = $state<string>(ALL);
	let uploadKind = $state<WordlistKind>(WORDLIST_KINDS[0]);
	let uploading = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);
	let removing = $state<Wordlist | null>(null);
	let deleting = $state(false);
	let viewing = $state<Wordlist | null>(null);
	const picked = new SvelteSet<string>();

	$effect(() => {
		untrack(() => store.fetch());
	});

	let items = $derived(
		kindFilter === ALL ? store.wordlists : store.wordlists.filter((w) => w.kind === kindFilter)
	);
	let counts = $derived(
		Object.fromEntries(
			WORDLIST_KINDS.map((k) => [k, store.wordlists.filter((w) => w.kind === k).length])
		) as Record<WordlistKind, number>
	);

	function toggleCheck(id: string) {
		if (picked.has(id)) picked.delete(id);
		else picked.add(id);
	}

	async function upload(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const chosen = Array.from(input.files ?? []);
		input.value = '';
		if (!chosen.length) return;
		if (chosen.length > MAX_WORDLIST_UPLOAD) {
			toast.error(
				`${chosen.length} files selected. The limit is ${MAX_WORDLIST_UPLOAD} per upload.`
			);
			return;
		}
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
					{ description: `${words.toLocaleString()} words` }
				);
			}
			for (const rejection of result.rejected) {
				toast.error(`${rejection.filename} not added`, { description: rejection.reason });
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Wordlists not uploaded');
		} finally {
			uploading = false;
		}
	}

	async function remove() {
		const target = removing;
		if (!target) return;
		deleting = true;
		try {
			if (await store.remove(target.id)) {
				picked.delete(target.id);
				toast.success(`${target.name} removed`);
			}
		} finally {
			deleting = false;
			removing = null;
		}
	}

	let lastChanged = $derived(
		store.wordlists
			.map((w) => w.updated_at)
			.sort()
			.at(-1) ?? null
	);
</script>

<div class="space-y-6">
	<Card.Root class="gap-0 py-0">
		<Card.Header class="border-b py-5">
			<Card.Title>Wordlists</Card.Title>
			{#if lastChanged}
				<Card.Description>Updated {relativeTime(lastChanged)}</Card.Description>
			{/if}
			<Card.Action class="flex items-center gap-2">
				<Select.Root type="single" bind:value={uploadKind}>
					<Select.Trigger class="w-[190px]" aria-label="Wordlist kind">
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
					loadingLabel="Uploading"
					onclick={() => fileInput?.click()}
				>
					<Upload class="size-4" /> Upload wordlists
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
					aria-label="Filter by kind"
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
						title="No wordlists"
						description="Plain text, one word per line."
					/>
				</div>
			{:else}
				{#each items as item (item.id)}
					<div
						class="group flex items-start gap-4 border-b px-6 py-4 last:border-b-0 hover:bg-muted/40"
					>
						{#if item.origin !== WordlistOrigin.BUILTIN}
							<div class="flex h-6 shrink-0 items-center">
								<Checkbox
									checked={picked.has(item.id)}
									onCheckedChange={() => toggleCheck(item.id)}
									aria-label="Select {item.name}"
								/>
							</div>
						{:else}
							<div class="w-4 shrink-0"></div>
						{/if}
						<div class="min-w-0 flex-1 space-y-1">
							<div class="flex flex-wrap items-center gap-2">
								<span class="font-medium">{item.name}</span>
								<Badge variant={WORDLIST_ORIGIN_BADGE[item.origin]}>
									{WORDLIST_ORIGIN_LABELS[item.origin]}
								</Badge>
								<Badge variant="outline">{WORDLIST_KIND_LABELS[item.kind]}</Badge>
							</div>
							{#if item.description}
								<p class="text-sm text-muted-foreground">{item.description}</p>
							{/if}
							<Hint text="Name used in a scan engine">
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
							<div>{formatBytes(item.bytes)}</div>
							<div>{relativeTime(item.updated_at)}</div>
						</div>

						<div class="flex shrink-0 items-center gap-1">
							<Hint text="Preview">
								{#snippet child(props)}
									<Button
										{...props}
										variant="ghost"
										size="icon"
										class="size-8"
										aria-label="Preview {item.name}"
										onclick={() => (viewing = item)}
									>
										<Eye class="size-4" />
									</Button>
								{/snippet}
							</Hint>
							<Hint
								text={item.origin === WordlistOrigin.BUILTIN
									? 'Default wordlists are read-only'
									: 'Remove'}
							>
								{#snippet child(props)}
									<span class="inline-flex">
										<Button
											{...props}
											variant="ghost"
											size="icon"
											class="size-8"
											aria-label="Remove {item.name}"
											disabled={item.origin === WordlistOrigin.BUILTIN}
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

<SelectionDeleteBar
	ids={[...picked]}
	noun="wordlist"
	removes="files"
	remove={(id) => wordlistsApi.remove(id)}
	onDone={async () => {
		picked.clear();
		await store.fetch(true);
	}}
	onClear={() => picked.clear()}
/>

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
	title="Remove wordlist"
	description={`Wordlist ${removing?.name ?? ''} and its file are removed.`}
	confirmLabel="Remove"
	isDeleting={deleting}
	onConfirm={remove}
/>
