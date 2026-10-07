<script lang="ts">
	import Flame from '@lucide/svelte/icons/flame';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Table from '$lib/components/ui/table';
	import Hint from '$lib/components/hint.svelte';
	import EvidenceMark from '$lib/components/evidence-mark.svelte';
	import CountryFlag from '$lib/components/scans/results/country-flag.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import { SEVERITY_CHIP, severityLabel } from '$lib/config/vulnerabilities';
	import { surfaceSpec } from '$lib/config/surface';
	import {
		httpStatusTextClass,
		STATUS_DOT,
		httpStatusClass
	} from '$lib/utilities/scan-correlation';
	import { BLOCK_COLUMNS, aboutRow, rowHref, rowLabel, type Cell } from './block-columns';
	import type { BlockRow } from '$lib/types/ask';

	interface Props {
		dimension: string;
		rows: BlockRow[];
		onAbout?: (about: string, label: string) => void;
	}

	let { dimension, rows, onAbout }: Props = $props();

	let columns = $derived(BLOCK_COLUMNS[dimension] ?? []);
	let noun = $derived(surfaceSpec(dimension)?.noun ?? 'row');
</script>

{#snippet cell(c: Cell)}
	{#if c.kind === 'mono'}
		<span
			class="font-mono text-xs leading-5 wrap-anywhere {c.strong
				? 'font-medium text-foreground'
				: 'text-muted-foreground'}">{c.text}</span
		>
	{:else if c.kind === 'text'}
		<span class="text-sm leading-5 wrap-anywhere {c.muted ? 'text-muted-foreground' : ''}"
			>{c.text}</span
		>
	{:else if c.kind === 'status'}
		{#if c.code == null}
			<span class="font-mono text-xs text-muted-foreground">—</span>
		{:else}
			<span
				class="inline-flex h-5 items-center gap-1.5 font-mono text-xs {httpStatusTextClass(c.code)}"
			>
				<span class="size-1.5 rounded-full {STATUS_DOT[httpStatusClass(c.code)]}"></span>
				{c.code}
			</span>
		{/if}
	{:else if c.kind === 'severity'}
		{#if c.value}
			<span class="inline-flex h-5 items-center gap-1.5">
				<span
					class="inline-flex h-5 items-center gap-1 rounded px-1.5 text-2xs font-semibold {SEVERITY_CHIP[
						c.value
					]?.chip ?? 'bg-muted text-muted-foreground'}"
				>
					{severityLabel(c.value)}{#if c.count && c.count > 1}<span class="font-normal tabular-nums"
							>· {c.count}</span
						>{/if}
				</span>
				{#if c.kev}
					<Flame class="size-3 text-destructive" aria-label="Known exploited" />
				{/if}
			</span>
		{/if}
	{:else if c.kind === 'tech'}
		<span class="flex flex-wrap items-center gap-1">
			{#each c.items as name (name)}
				<span
					class="inline-flex h-5 items-center gap-1 rounded border bg-muted/40 px-1.5 text-2xs whitespace-nowrap text-muted-foreground"
				>
					<TechIcon {name} class="size-3" />
					{name}
				</span>
			{/each}
			{#if c.more > 0}
				<span class="text-2xs text-muted-foreground tabular-nums">+{c.more}</span>
			{/if}
		</span>
	{:else if c.kind === 'country'}
		<CountryFlag code={c.code} class="text-xs" />
	{:else if c.kind === 'evidence'}
		{#if c.value}<EvidenceMark evidence={c.value} />{/if}
	{:else if c.kind === 'kev'}
		{#if c.on}
			<Badge variant="destructive" class="gap-1 px-1.5 text-2xs font-normal">
				<Flame class="size-2.5" /> KEV
			</Badge>
		{/if}
	{/if}
{/snippet}

<Table.Root class="border-collapse">
	<Table.Header>
		<Table.Row>
			{#each columns as col (col.key)}
				<Table.Head class="first:pl-4 {col.width}">
					{col.label}
				</Table.Head>
			{/each}
			<Table.Head class="w-10 pr-3"><span class="sr-only">Actions</span></Table.Head>
		</Table.Row>
	</Table.Header>
	<Table.Body>
		{#each rows as row, i (i)}
			{@const href = rowHref(dimension, row)}
			<Table.Row class="group">
				{#each columns as col, j (col.key)}
					<Table.Cell class="align-top whitespace-normal first:pl-4 {col.width}">
						{#if j === 0 && href}
							<a
								{href}
								class="block rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
							>
								{@render cell(col.cell(row))}
							</a>
						{:else}
							{@render cell(col.cell(row))}
						{/if}
					</Table.Cell>
				{/each}
				<Table.Cell class="w-10 text-right align-top">
					{#if onAbout}
						<Hint text="Ask about this {noun}">
							{#snippet child(props)}
								<Button
									{...props}
									variant="ghost"
									size="icon-xs"
									class="text-muted-foreground opacity-0 group-hover:opacity-100 pointer-coarse:opacity-100 hover:text-primary focus-visible:opacity-100"
									onclick={() => onAbout(aboutRow(dimension, row), rowLabel(dimension, row))}
									aria-label="Ask about this {noun}"
								>
									<Sparkles class="size-3.5" />
								</Button>
							{/snippet}
						</Hint>
					{/if}
				</Table.Cell>
			</Table.Row>
		{/each}
	</Table.Body>
</Table.Root>
