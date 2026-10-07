<script lang="ts">
	import * as Table from '$lib/components/ui/table';
	import CodeBlock from '$lib/components/code-block.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import HeroBlock from './hero-block.svelte';
	import IdentityMark from './identity-mark.svelte';
	import ResultCell from './result-cell.svelte';
	import SelectableTable from './selectable-table.svelte';
	import Info from '@lucide/svelte/icons/info';
	import { TONE_CHIP, TONE_DOT, TONE_TINT } from '$lib/config/toolbox';
	import { isExternalHref, safeHref } from '$lib/utilities/links';
	import type { CodeLang } from '$lib/utilities/code-highlight';
	import type { Lookup, ResultBlock, Tone } from '$lib/types/toolbox';

	interface Props {
		block: ResultBlock;
		organization?: string | null;
		onLookup?: (value: string, tool: string | null) => void;
		onNavigate?: () => void;
	}

	let { block, organization = null, onLookup, onNavigate }: Props = $props();

	const count = $derived(
		block.rows.length || block.facts.length || block.tags.length || (block.text ? 1 : 0)
	);
	const ROW_PAGE = 8;
	let expanded = $state(false);
	const shownRows = $derived(expanded ? block.rows : block.rows.slice(0, ROW_PAGE));
	const folded = $derived(block.rows.length - shownRows.length);
	const hidden = $derived(
		block.total !== null && block.total > block.rows.length ? block.total - block.rows.length : 0
	);
	const DOTTED: Tone[] = ['success', 'warning', 'critical', 'info'];
	const chase = (l: Lookup | null) => l && onLookup && (() => onLookup(l.value, l.tool));
</script>

{#if block.kind === 'hero'}
	<HeroBlock {block} />
{:else}
	{#if block.title && block.kind !== 'note'}
		<div class="pb-1.5">
			<SectionHead
				title={block.title}
				count={block.total !== null && block.total > 0 ? block.total.toLocaleString() : null}
			/>
		</div>
	{/if}

	{#if block.kind === 'image'}
		<img
			src={block.src}
			alt={block.title ?? ''}
			class="max-h-56 w-full rounded-md border bg-muted/30 object-cover object-top"
		/>
		{#if block.sub}<p class="pt-1 text-2xs text-muted-foreground">{block.sub}</p>{/if}
	{:else if count === 0}
		<p class="pb-1 text-sm text-muted-foreground">{block.empty}</p>
	{:else if block.kind === 'facts'}
		<dl class="grid">
			{#each block.facts as f (f.label)}
				{@const go = chase(f.lookup)}
				{@const href = safeHref(f.href)}
				<div
					class="flex items-start gap-3 border-b border-border/60 py-1.5 leading-5 last:border-0"
				>
					<dt class="w-36 shrink-0 text-xs text-muted-foreground">{f.label}</dt>
					<dd class="flex min-w-0 flex-1 items-start gap-1.5">
						{#if DOTTED.includes(f.tone)}
							<span class="flex h-5 shrink-0 items-center">
								<span class="size-1.5 rounded-full {TONE_DOT[f.tone]}"></span>
							</span>
						{:else if f.identity}
							<span class="flex h-5 shrink-0 items-center">
								<IdentityMark identity={f.identity} class="size-3.5" />
							</span>
						{/if}
						<span class="min-w-0 flex-1 break-words">
							<span
								class="text-sm {TONE_TINT[f.tone]} {f.mono ? 'font-mono text-xs break-all' : ''}"
							>
								{#if href}
									<a
										{href}
										target={isExternalHref(href) ? '_blank' : undefined}
										rel={isExternalHref(href) ? 'noreferrer' : undefined}
										onclick={() => !isExternalHref(href) && onNavigate?.()}
										class="hover:text-primary">{f.value}</a
									>
								{:else if go}
									<button type="button" onclick={go} class="text-left hover:text-primary"
										>{f.value}</button
									>
								{:else}
									{f.value}
								{/if}
							</span>
							{#if f.note}
								<span class="text-xs text-muted-foreground"> · {f.note}</span>
							{/if}
						</span>
						{#if f.mono}
							<span class="flex h-5 shrink-0 items-center">
								<CopyButton value={f.value} />
							</span>
						{/if}
					</dd>
				</div>
			{/each}
		</dl>
	{:else if block.kind === 'table' && block.action}
		<SelectableTable {block} {organization} {onLookup} {onNavigate} />
	{:else if block.kind === 'table'}
		<Table.Root>
			<Table.Header>
				<Table.Row>
					{#each block.columns as column (column)}
						<Table.Head>{column}</Table.Head>
					{/each}
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each shownRows as row, i (i)}
					<Table.Row>
						{#each row as c, j (j)}
							<Table.Cell class="align-top whitespace-normal">
								<ResultCell cell={c} {onLookup} {onNavigate} />
							</Table.Cell>
						{/each}
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
		{#if folded > 0}
			<button
				type="button"
				onclick={() => (expanded = true)}
				class="w-full border-t border-border/60 px-2 pt-1.5 text-left text-xs text-muted-foreground hover:text-foreground"
			>
				Show {folded} more
			</button>
		{:else if hidden > 0}
			<p class="px-2 pt-1.5 text-xs text-muted-foreground">{hidden} more not shown.</p>
		{/if}
	{:else if block.kind === 'tags'}
		<div class="flex flex-wrap gap-1.5">
			{#each block.tags as t, i (`${i}:${t.value}`)}
				{@const go = chase(t.lookup)}
				{#if go}
					<button
						type="button"
						onclick={go}
						class="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs hover:border-foreground/25 hover:bg-accent {TONE_CHIP[
							t.tone
						]}"
					>
						{#if t.identity}<IdentityMark identity={t.identity} class="size-3" />{/if}
						{t.value}
					</button>
				{:else}
					<span
						class="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs {TONE_CHIP[
							t.tone
						]}"
					>
						{#if t.identity}<IdentityMark identity={t.identity} class="size-3" />{/if}
						{t.value}
					</span>
				{/if}
			{/each}
		</div>
	{:else if block.kind === 'code'}
		<CodeBlock
			code={block.text ?? ''}
			lang={(block.lang ?? 'text') as CodeLang}
			maxLines={12}
			maxHeight="18rem"
		/>
	{:else if block.kind === 'note'}
		<div
			class="flex items-start gap-2 rounded-md border px-2.5 py-2 text-sm leading-5 {TONE_CHIP[
				block.tone
			]}"
		>
			<span class="flex h-5 shrink-0 items-center"><Info class="size-3.5" /></span>
			<span class="min-w-0">{block.text}</span>
		</div>
	{/if}
{/if}
