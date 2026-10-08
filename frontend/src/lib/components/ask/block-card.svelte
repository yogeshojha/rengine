<script lang="ts">
	import { IME_KEY_CODE } from '$lib/constants';
	import { linkScan, linkValues } from './link-scope';
	import { tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Copy from '@lucide/svelte/icons/copy';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Pencil from '@lucide/svelte/icons/pencil';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import Hint from '$lib/components/hint.svelte';
	import BlockRows from './block-rows.svelte';
	import BlockGroups from './block-groups.svelte';
	import BlockCve from './block-cve.svelte';
	import BlockCauses from './block-causes.svelte';
	import BlockFacts from './block-facts.svelte';
	import ReadAs from './read-as.svelte';
	import { blockHref } from './block-columns';
	import { estateApi } from '$lib/api/ask';
	import { BLOCK_ROWS, BlockKind, MAX_BLOCK_QUERY } from '$lib/config/ask';
	import { ROUTES } from '$lib/config/routes';
	import { surfaceSpec } from '$lib/config/surface';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { cn } from '$lib/utils.js';
	import type { AnswerBlock, BlockCause, BlockData, BlockFact, PinnedQuery } from '$lib/types/ask';

	interface Props {
		block: AnswerBlock;
		data: BlockData | undefined;
		threadId: string | null;
		filtered: boolean;
		focused?: boolean;
		lead?: boolean;
		busy?: boolean;
		offline?: boolean;
		onAbout?: (about: string, label: string) => void;
		onChange?: (block: AnswerBlock, data: BlockData, threadId: string) => void;
		onPin?: (text: string, pinned: PinnedQuery, about: string) => void;
	}

	let {
		block,
		data,
		threadId,
		filtered,
		focused = false,
		lead = false,
		busy = false,
		offline = false,
		onAbout,
		onChange,
		onPin
	}: Props = $props();

	const scan = linkScan();
	const values = linkValues();

	let spec = $derived(surfaceSpec(block.dimension ?? ''));
	let Icon = $derived(block.kind === BlockKind.CVE ? ShieldAlert : spec?.icon);
	let kindLabel = $derived(block.kind === BlockKind.CVE ? 'CVE record' : (spec?.label ?? ''));
	let heading = $derived(block.title ? block.title : kindLabel);
	let total = $derived(data?.total ?? block.total);
	let capped = $derived(data?.capped ?? block.capped);
	let noun = $derived(total === 1 ? (spec?.noun ?? 'row') : (spec?.nounPlural ?? 'rows'));
	let scopeValues = $derived(filtered ? (data?.scope_values ?? values()) : null);
	let href = $derived(
		block.kind === BlockKind.CVE
			? block.cve && !filtered
				? ROUTES.cve(block.cve)
				: null
			: blockHref(block.dimension, block.query, scopeValues, scan())
	);
	let openLabel = $derived(
		block.kind === BlockKind.CVE ? 'Open CVE page' : `Open in ${spec?.label ?? 'results'}`
	);
	let moved = $derived(
		!block.edited && data?.total != null && block.total != null && data.total !== block.total
	);
	let causes = $derived(block.kind === BlockKind.ROWS ? (data?.causes ?? null) : null);
	let facts = $derived(block.kind === BlockKind.ROWS ? (data?.facts ?? []) : []);
	let empty = $derived(block.kind !== BlockKind.CVE && !!data && !data.error && total === 0);
	let opened = $state(false);
	let showRows = $derived(!causes || opened);

	let rows = $derived<BlockData['rows']>(data?.rows ?? []);
	let more = $state(false);
	let editing = $state(false);
	let draft = $state('');
	let saving = $state(false);
	let editError = $state('');
	let input = $state<HTMLInputElement | null>(null);

	let drained = $state<BlockData | undefined>(undefined);
	let rest = $derived(total != null && drained !== data ? total - rows.length : 0);

	async function loadMore() {
		if (!threadId || more) return;
		const asked = data;
		more = true;
		try {
			const page = await estateApi.page(threadId, block.id, rows.length);
			if (asked !== data) return;
			if (page.rows.length) rows = [...rows, ...page.rows];
			else drained = data;
		} catch (e) {
			toast.error((e as Error).message);
		} finally {
			more = false;
		}
	}

	async function startEdit() {
		draft = block.query ?? '';
		editError = '';
		editing = true;
		await tick();
		input?.focus();
		input?.select();
	}

	async function saveEdit() {
		const query = draft.trim();
		if (!threadId || !query || saving) return;
		if (query === block.query) {
			editing = false;
			return;
		}
		const forThread = threadId;
		saving = true;
		editError = '';
		try {
			const fresh = await estateApi.editQuery(forThread, block.id, query);
			onChange?.(
				{ ...block, query, total: fresh.total, capped: fresh.capped, edited: true },
				fresh,
				forThread
			);
			editing = false;
		} catch (e) {
			editError = (e as Error).message;
		} finally {
			saving = false;
		}
	}

	function onKey(e: KeyboardEvent) {
		if (e.isComposing || e.keyCode === IME_KEY_CODE) return;
		if (e.key === 'Enter') {
			e.preventDefault();
			void saveEdit();
		} else if (e.key === 'Escape') {
			e.preventDefault();
			editing = false;
		}
	}

	async function copyQuery() {
		if (block.query && (await writeClipboard(block.query))) toast.success('Query copied');
	}

	function askAbout() {
		const label = block.title || (block.cve ?? `${total ?? ''} ${noun}`.trim());
		onAbout?.(block.id, label);
	}

	function onCause(cause: BlockCause) {
		if (!cause.query || !causes) return;
		const plural = spec?.nounPlural ?? 'rows';
		const one = spec?.noun ?? 'row';
		const where = `${causes.prep} ${cause.label}`;
		const text =
			cause.count === 1
				? `Show the ${one} ${where}`
				: `Show the ${cause.count.toLocaleString()} ${plural} ${where}`;
		onPin?.(
			text,
			{ dimension: block.dimension ?? '', query: cause.query, title: `${plural} ${where}` },
			block.id
		);
	}

	function onFact(fact: BlockFact) {
		const base = block.title ? block.title : (spec?.nounPlural ?? 'rows');
		onPin?.(
			fact.question,
			{ dimension: block.dimension ?? '', query: fact.query, title: `${base}, ${fact.title}` },
			block.id
		);
	}
</script>

<section
	id="block-{block.id}"
	class={cn(
		'scroll-mt-24 overflow-hidden rounded-lg border bg-card',
		focused && 'ring-2 ring-primary/40'
	)}
	aria-label="{block.id} {kindLabel}"
>
	<header class={cn('flex flex-col gap-1.5 px-4 py-2.5', !empty && 'border-b')}>
		<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
			<span
				class="inline-flex h-5 shrink-0 items-center rounded bg-primary/10 px-1.5 font-mono text-2xs font-semibold text-primary"
				>{block.id}</span
			>
			{#if Icon}
				<Icon class="size-3.5 shrink-0 text-muted-foreground" />
			{/if}
			<span class="min-w-0 flex-1 basis-32 truncate text-sm font-medium">{heading}</span>
			<span class="ml-auto flex shrink-0 items-center gap-1">
				{#if block.kind !== BlockKind.CVE && total != null}
					<span class="mr-1 text-sm font-semibold tabular-nums">
						{total.toLocaleString()}{capped ? '+' : ''}
						<span class="font-normal text-muted-foreground">{noun}</span>
					</span>
				{/if}
				{#if onAbout}
					<Hint text="Ask about {block.id}">
						{#snippet child(props)}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								class="size-7 text-muted-foreground hover:text-primary"
								onclick={askAbout}
								aria-label="Ask about {block.id}"
							>
								<Sparkles class="size-3.5" />
							</Button>
						{/snippet}
					</Hint>
				{/if}
				{#if href}
					<Hint text={openLabel}>
						{#snippet child(props)}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								class="size-7 text-muted-foreground"
								{href}
								aria-label={openLabel}
							>
								<ArrowUpRight class="size-3.5" />
							</Button>
						{/snippet}
					</Hint>
				{/if}
				{#if block.kind !== BlockKind.CVE}
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon-sm"
									class="size-7 text-muted-foreground"
									aria-label="Block actions"
								>
									<Ellipsis class="size-3.5" />
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end" class="w-44">
							<DropdownMenu.Item onclick={() => void startEdit()} disabled={!threadId}>
								<Pencil /> Edit query
							</DropdownMenu.Item>
							<DropdownMenu.Item onclick={() => void copyQuery()} disabled={!block.query}>
								<Copy /> Copy query
							</DropdownMenu.Item>
						</DropdownMenu.Content>
					</DropdownMenu.Root>
				{/if}
			</span>
		</div>

		{#if editing}
			<div class="flex flex-col gap-1.5">
				<div class="flex items-center gap-2">
					<input
						bind:this={input}
						bind:value={draft}
						onkeydown={onKey}
						maxlength={MAX_BLOCK_QUERY}
						spellcheck="false"
						autocomplete="off"
						aria-label="Query"
						class="h-8 min-w-0 flex-1 rounded-md border bg-background px-2.5 font-mono text-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/70"
					/>
					<Button
						size="sm"
						class="h-8"
						onclick={() => void saveEdit()}
						disabled={saving || !draft.trim()}
					>
						{#if saving}<Spinner class="size-3.5" />{/if}
						Run
					</Button>
					<Button size="sm" variant="ghost" class="h-8" onclick={() => (editing = false)}
						>Cancel</Button
					>
				</div>
				{#if editError}
					<span class="text-xs text-destructive">{editError}</span>
				{/if}
			</div>
		{:else if block.kind === BlockKind.CVE}
			<span class="font-mono text-xs text-muted-foreground">{block.cve}</span>
		{:else if !lead || block.edited || moved}
			<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
				{#if !lead}
					<ReadAs
						dimension={block.dimension}
						reading={data?.reading ?? []}
						query={block.query}
						label={false}
					/>
				{/if}
				{#if block.group_by}
					<span class="text-2xs text-muted-foreground">grouped</span>
				{/if}
				{#if block.edited}
					<span class="rounded bg-muted px-1.5 text-2xs text-muted-foreground">Edited</span>
				{/if}
				{#if moved && block.total != null}
					<Hint text="Count when the question was asked">
						{#snippet child(props)}
							<span {...props} class="text-2xs text-muted-foreground tabular-nums"
								>{(block.total ?? 0).toLocaleString()}{block.capped ? '+' : ''} then</span
							>
						{/snippet}
					</Hint>
				{/if}
			</div>
		{/if}
	</header>

	{#if !data}
		<div class="flex flex-col gap-2 px-4 py-3">
			<Skeleton class="h-4 w-full" />
			<Skeleton class="h-4 w-11/12" />
			<Skeleton class="h-4 w-4/5" />
		</div>
	{:else if data.error}
		<p class="m-0 px-4 py-3 text-sm text-destructive">{data.error}</p>
	{:else if block.kind === BlockKind.CVE && data.record}
		<BlockCve record={data.record} />
	{:else if empty}
		<!-- the header carries the zero -->
	{:else if block.kind === BlockKind.GROUPS}
		{#if data.groups.length}
			<BlockGroups
				dimension={block.dimension ?? ''}
				groupBy={block.group_by}
				query={block.query}
				groups={data.groups}
				{scopeValues}
			/>
		{:else}
			<p class="m-0 px-4 py-3 text-sm text-muted-foreground">No groups</p>
		{/if}
	{:else}
		{#if causes}
			<BlockCauses
				dimension={block.dimension ?? ''}
				{causes}
				total={total ?? 0}
				{capped}
				{scopeValues}
				disabled={busy || offline || !onPin}
				{onCause}
			/>
		{/if}
		{#if showRows && rows.length}
			<div class={cn(causes && 'border-t')}>
				<BlockRows dimension={block.dimension ?? ''} {rows} {onAbout} />
			</div>
		{/if}
	{/if}

	{#if data && !data.error && !empty && facts.length}
		<BlockFacts
			total={total ?? 0}
			{capped}
			{facts}
			disabled={busy || offline || !onPin}
			dimension={block.dimension}
			{scopeValues}
			links={offline}
			{onFact}
		/>
	{/if}

	{#if data && !data.error && !empty && block.kind === BlockKind.ROWS && rows.length}
		<footer
			class="flex flex-wrap items-center gap-x-4 gap-y-1 border-t bg-muted/20 px-4 py-2 text-xs"
		>
			{#if causes}
				<button
					type="button"
					class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
					aria-expanded={opened}
					onclick={() => (opened = !opened)}
				>
					<ChevronDown class={cn('size-3.5', !opened && '-rotate-90')} />
					{(total ?? 0).toLocaleString()}{capped ? '+' : ''}
					{noun}
				</button>
			{/if}
			<span class="ml-auto flex items-center gap-3">
				{#if showRows && rest > 0}
					<Button
						variant="ghost"
						size="sm"
						class="h-7 px-2 text-xs"
						onclick={() => void loadMore()}
						disabled={more || !threadId}
					>
						{#if more}<Spinner class="size-3" />{/if}
						Show {Math.min(rest, BLOCK_ROWS)} more
					</Button>
				{/if}
				{#if href}
					<a {href} class="inline-flex items-center gap-1 font-medium text-primary">
						{openLabel}
						<ArrowUpRight class="size-3" />
					</a>
				{/if}
			</span>
		</footer>
	{/if}
</section>
