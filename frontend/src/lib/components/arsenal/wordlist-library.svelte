<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Eye from '@lucide/svelte/icons/eye';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Upload from '@lucide/svelte/icons/upload';
	import * as Card from '$lib/components/ui/card';
	import * as Select from '$lib/components/ui/select';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import SelectionDeleteBar from '$lib/components/selection-delete-bar.svelte';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { SvelteSet } from 'svelte/reactivity';
	import WordlistSheet from './wordlist-sheet.svelte';
	import { wordlists as store } from '$lib/stores/wordlists.svelte';
	import { wordlistsApi } from '$lib/api/wordlists';
	import { auth } from '$lib/stores/auth.svelte';
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

	const isAdmin = $derived(auth.user?.is_superuser ?? false);

	let kindFilter = $state<string>(ALL);
	let uploadKind = $state<WordlistKind>(WORDLIST_KINDS[0]);
	let uploading = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);
	let removing = $state<Wordlist | null>(null);
	let deleting = $state(false);
	let viewing = $state<Wordlist | null>(null);
	let attempted = $state(false);
	const picked = new SvelteSet<string>();

	$effect(() => {
		untrack(() => store.fetch().finally(() => (attempted = true)));
	});

	let failed = $derived(attempted && !store.hasFetched && !store.isLoading);

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
				toast.success(`${target.name} deleted`);
				removing = null;
			}
		} finally {
			deleting = false;
		}
	}

	let lastChanged = $derived(
		store.wordlists
			.map((w) => w.updated_at)
			.sort()
			.at(-1) ?? null
	);
</script>

<div class="max-w-5xl space-y-6">
	<Card.Root class="gap-0 overflow-hidden py-0">
		<Card.Header class="border-b px-4 py-5">
			<Card.Title>Wordlists</Card.Title>
			{#if lastChanged}
				<Card.Description>Updated {relativeTime(lastChanged)}</Card.Description>
			{/if}
			<Card.Action class="flex flex-wrap items-center justify-end gap-2">
				<Label for="wordlist-upload-kind" class="text-xs font-normal text-muted-foreground">
					Upload as
				</Label>
				<Select.Root type="single" bind:value={uploadKind} disabled={!isAdmin}>
					<Select.Trigger id="wordlist-upload-kind" size="sm" class="w-[190px]">
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
				<Hint text={isAdmin ? null : 'Editable by administrators'}>
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<LoadingButton
								size="sm"
								loading={uploading}
								loadingLabel="Uploading"
								disabled={!isAdmin}
								onclick={() => fileInput?.click()}
							>
								<Upload class="size-4" /> Upload wordlists
							</LoadingButton>
						</span>
					{/snippet}
				</Hint>
			</Card.Action>
		</Card.Header>

		<Card.Content class="p-0">
			<div class="border-b px-4 py-3">
				<ToggleGroup.Root
					type="single"
					variant="outline"
					spacing={1}
					value={kindFilter}
					onValueChange={(v) => (kindFilter = v || ALL)}
					class="flex-wrap justify-start"
					aria-label="Filter by kind"
				>
					<ToggleGroup.Item value={ALL} class="h-9 gap-1.5 px-3 text-sm font-normal">
						All
						{#if store.hasFetched}
							<span class="text-muted-foreground tabular-nums">{store.wordlists.length}</span>
						{/if}
					</ToggleGroup.Item>
					{#each WORDLIST_KINDS as kind (kind)}
						<ToggleGroup.Item value={kind} class="h-9 gap-1.5 px-3 text-sm font-normal">
							{WORDLIST_KIND_LABELS[kind]}
							{#if store.hasFetched}
								<span class="text-muted-foreground tabular-nums">{counts[kind]}</span>
							{/if}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
			</div>

			{#if failed}
				<EmptyState
					icon={TriangleAlert}
					title="Wordlists not loaded"
					description={store.error ?? undefined}
					class="rounded-none border-0 bg-transparent py-16"
				>
					<Button variant="outline" size="sm" onclick={() => store.fetch()}>Retry</Button>
				</EmptyState>
			{:else if !store.hasFetched}
				<RowSkeleton rows={4} avatar={null} trailing="h-8 w-24 rounded-md" />
			{:else if !items.length}
				<EmptyState
					icon={Upload}
					title="No wordlists"
					description="Plain text, one word per line."
					class="rounded-none border-0 bg-transparent py-16"
				/>
			{:else}
				{#each items as item (item.id)}
					<div
						class="group flex items-start gap-3 border-b px-4 py-3 last:border-b-0 hover:bg-muted/40"
					>
						{#if item.origin !== WordlistOrigin.BUILTIN && isAdmin}
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
								<span class="text-sm leading-5 font-medium">{item.name}</span>
								<Badge variant={WORDLIST_ORIGIN_BADGE[item.origin]}>
									{WORDLIST_ORIGIN_LABELS[item.origin]}
								</Badge>
								<Badge variant="outline">{WORDLIST_KIND_LABELS[item.kind]}</Badge>
							</div>
							{#if item.description}
								<p class="text-xs text-muted-foreground">{item.description}</p>
							{/if}
							<Hint text="Name used in a scan engine">
								{#snippet child(props)}
									<code
										{...props}
										class="inline-block rounded-md border bg-muted/60 px-1.5 py-0.5 font-mono text-xs text-muted-foreground"
										>{item.slug}</code
									>
								{/snippet}
							</Hint>
						</div>

						<div class="w-28 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
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
										size="icon-sm"
										aria-label="Preview {item.name}"
										onclick={() => (viewing = item)}
									>
										<Eye class="size-4" />
									</Button>
								{/snippet}
							</Hint>
							{#if item.origin !== WordlistOrigin.BUILTIN && isAdmin}
								<Hint text="Delete">
									{#snippet child(props)}
										<Button
											{...props}
											variant="ghost"
											size="icon-sm"
											aria-label="Delete {item.name}"
											onclick={() => (removing = item)}
										>
											<Trash2 class="size-4" />
										</Button>
									{/snippet}
								</Hint>
							{:else if item.origin !== WordlistOrigin.BUILTIN}
								<Hint text="Editable by administrators">
									{#snippet child(props)}
										<span {...props} class="inline-flex">
											<Button
												variant="ghost"
												size="icon-sm"
												aria-label="Delete {item.name}"
												disabled
											>
												<Trash2 class="size-4" />
											</Button>
										</span>
									{/snippet}
								</Hint>
							{:else}
								<span class="size-8" aria-hidden="true"></span>
							{/if}
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
		if (store.error) toast.error('Wordlists not refreshed');
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
	title="Delete wordlist"
	description={`Wordlist ${removing?.name ?? ''} and its file are removed.`}
	confirmLabel="Delete"
	loadingLabel="Deleting"
	isDeleting={deleting}
	onConfirm={remove}
/>
