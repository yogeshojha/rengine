<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import CodeBlock from '$lib/components/code-block.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Info from '@lucide/svelte/icons/info';
	import { TONE_CHIP, TONE_DOT, TONE_TEXT } from '$lib/config/toolbox';
	import type { CodeLang } from '$lib/utilities/code-highlight';
	import type { ResultBlock, Tone } from '$lib/types/toolbox';

	let { block }: { block: ResultBlock } = $props();

	const count = $derived(
		block.rows.length || block.facts.length || block.tags.length || (block.text ? 1 : 0)
	);
	const hidden = $derived(
		block.total !== null && block.total > block.rows.length ? block.total - block.rows.length : 0
	);
	const external = (href: string) => href.startsWith('http');
	// colour carries state on the dot; only what you must notice tints the value too
	const DOTTED: Tone[] = ['success', 'warning', 'critical', 'info'];
	const TINTED: Record<Tone, string> = {
		...TONE_TEXT,
		info: TONE_TEXT.neutral
	};
</script>

{#if block.title && block.kind !== 'note'}
	<div class="flex items-baseline gap-2 pb-1.5">
		<h4 class="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
			{block.title}
		</h4>
		{#if block.total !== null && block.total > 0}
			<span class="font-mono text-[11px] text-muted-foreground/70">{block.total}</span>
		{/if}
	</div>
{/if}

{#if count === 0}
	<p class="pb-1 text-[13px] text-muted-foreground">{block.empty}</p>
{:else if block.kind === 'facts'}
	<dl class="grid">
		{#each block.facts as f (f.label)}
			<div class="flex items-start gap-3 border-b border-border/40 py-1.5 leading-5 last:border-0">
				<dt class="w-36 shrink-0 text-xs text-muted-foreground">{f.label}</dt>
				<dd class="flex min-w-0 flex-1 items-start gap-1.5">
					{#if DOTTED.includes(f.tone)}
						<span class="flex h-5 shrink-0 items-center">
							<span class="size-1.5 rounded-full {TONE_DOT[f.tone]}"></span>
						</span>
					{/if}
					<span class="min-w-0 flex-1 break-words">
						<span
							class="text-[13px] {TINTED[f.tone]} {f.mono ? 'font-mono text-xs break-all' : ''}"
						>
							{#if f.href}
								<a
									href={f.href}
									target={external(f.href) ? '_blank' : undefined}
									rel={external(f.href) ? 'noreferrer' : undefined}
									class="underline-offset-2 hover:underline">{f.value}</a
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
						<CopyButton value={f.value} class="size-5" />
					{/if}
				</dd>
			</div>
		{/each}
	</dl>
{:else if block.kind === 'table'}
	<ScrollArea orientation="horizontal" class="w-full">
		<table class="w-full min-w-full text-left">
			<thead>
				<tr class="border-b border-border">
					{#each block.columns as column (column)}
						<th
							class="pb-1.5 pr-4 text-[11px] font-medium tracking-wide text-muted-foreground uppercase last:pr-0"
						>
							{column}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each block.rows as row, i (i)}
					<tr class="border-b border-border/40 last:border-0">
						{#each row as c, j (j)}
							<td class="py-1 pr-4 align-top last:pr-0">
								<span
									class="text-[13px] leading-5 {TINTED[c.tone]} {c.mono
										? 'font-mono text-xs break-all'
										: 'break-words'}"
								>
									{#if c.href}
										<a
											href={c.href}
											target={external(c.href) ? '_blank' : undefined}
											rel={external(c.href) ? 'noreferrer' : undefined}
											class="inline-flex items-center gap-1 underline-offset-2 hover:underline"
										>
											{c.value}
											{#if external(c.href)}<ArrowUpRight class="size-3 shrink-0" />{/if}
										</a>
									{:else}
										{c.value}
									{/if}
								</span>
								{#if c.note}
									<span class="text-xs text-muted-foreground"> {c.note}</span>
								{/if}
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</ScrollArea>
	{#if hidden > 0}
		<p class="pt-1.5 text-xs text-muted-foreground">{hidden} more not shown.</p>
	{/if}
{:else if block.kind === 'tags'}
	<div class="flex flex-wrap gap-1.5">
		{#each block.tags as t (t.value)}
			<span
				class="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs {TONE_CHIP[
					t.tone
				]}"
			>
				{#if t.icon}<TechIcon name={t.icon} class="size-3" />{/if}
				{t.value}
			</span>
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
		class="flex items-start gap-2 rounded-md border px-2.5 py-2 text-[13px] leading-5 {TONE_CHIP[
			block.tone
		]}"
	>
		<span class="flex h-5 shrink-0 items-center"><Info class="size-3.5" /></span>
		<span class="min-w-0">{block.text}</span>
	</div>
{/if}
