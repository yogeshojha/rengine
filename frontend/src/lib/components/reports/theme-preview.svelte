<script lang="ts">
	import { cn } from '$lib/utils.js';
	import { fontStack } from '$lib/config/reports';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import type { ThemeSummary } from '$lib/types/report';

	let {
		theme,
		variant = 'page',
		class: className = ''
	}: { theme: ThemeSummary; variant?: 'page' | 'cover' | 'spread'; class?: string } = $props();

	const fonts = $derived(reportCatalog.catalog?.fonts ?? []);
	const heading = $derived(fontStack(theme.heading_font, fonts));
	const body = $derived(fontStack(theme.body_font, fonts));
	const mono = $derived(fontStack(theme.mono_font, fonts));
	const caseOf = $derived(theme.uppercase_labels ? 'uppercase' : 'none');
	const layout = $derived(theme.cover_layout);
	const onDark = $derived(layout === 'full');
	const ground = $derived(onDark ? theme.cover_background : theme.page);
	const inkOn = $derived(onDark ? theme.cover_ink : theme.ink);

	const SEV = ['critical', 'high', 'medium', 'low', 'info'];
	const COUNTS = [20, 0, 4, 13, 589];
	const LINES = [100, 100, 97, 100, 62];
	const ROWS = ['critical', 'medium', 'low'];
</script>

{#snippet bar(width: string, tone: string, height = '1.5px', opacity = 1)}
	<div
		style="width:{width};height:{height};background:{tone};opacity:{opacity};border-radius:1px"
	></div>
{/snippet}

{#snippet identity(inset: string, ruled: boolean, size = '13cqw')}
	<div class="absolute" style="left:{inset};right:{inset};bottom:{inset}">
		{#if ruled}
			{@render bar('30%', theme.accent, '1.5px')}
			<div class="h-2"></div>
		{/if}
		<div
			class="line-clamp-2 leading-[1.1] font-semibold"
			style="font-family:{heading};letter-spacing:-0.025em;font-size:{size}"
		>
			Security Assessment
		</div>
		<div class="mt-[3%] opacity-70" style="font-family:{mono};font-size:7.5cqw">example.com</div>
		<div class="mt-2.5 flex gap-2">
			{#each [0, 1, 2] as n (n)}
				<div class="flex-1 space-y-1">
					{@render bar('60%', 'currentColor', '1px', 0.55)}
					{@render bar('100%', 'currentColor', '1.5px', 0.9)}
				</div>
			{/each}
		</div>
	</div>
{/snippet}

{#snippet grade(border: string)}
	<div
		class="absolute aspect-square w-[24%] rounded-full border"
		style="top:8%;right:9%;border-color:{border}"
	></div>
{/snippet}

{#snippet cover()}
	<div
		class="relative h-full overflow-hidden [container-type:inline-size]"
		style="background:{ground};color:{inkOn}"
	>
		{#if layout === 'band'}
			<div
				class="absolute inset-x-0 top-0 h-[52%]"
				style="background:{theme.cover_background};color:{theme.cover_ink}"
			>
				{@render identity('9%', false, '11cqw')}
				{@render grade(theme.cover_ink)}
			</div>
			<div class="absolute" style="left:9%;right:9%;bottom:9%">
				<div class="flex gap-2">
					{#each [0, 1] as n (n)}
						<div class="flex-1 space-y-1">
							{@render bar('55%', theme.ink_faint, '1px')}
							{@render bar('100%', theme.ink_soft, '1.5px')}
						</div>
					{/each}
				</div>
			</div>
		{:else if layout === 'split'}
			<div
				class="absolute inset-y-0 right-0 w-[42%]"
				style="background:{theme.cover_background};color:{theme.cover_ink}"
			>
				<div
					class="absolute aspect-square w-[57%] rounded-full border"
					style="top:11%;right:21%;border-color:currentColor"
				></div>
			</div>
			<div class="absolute inset-y-0 left-0 w-[58%]">
				{@render identity('10%', false, '9cqw')}
			</div>
		{:else}
			{#if layout === 'rule'}
				<div
					class="absolute inset-0 opacity-25"
					style="background-image:linear-gradient(to right,{theme.accent} 0.5px,transparent 0.5px),linear-gradient(to bottom,{theme.accent} 0.5px,transparent 0.5px);background-size:10px 10px"
				></div>
			{:else if theme.cover_art !== 'none'}
				<div
					class="absolute inset-0 opacity-30"
					style="background-image:radial-gradient({theme.accent} 0.6px,transparent 0.6px);background-size:7px 7px"
				></div>
			{/if}
			{@render identity('9%', layout === 'rule')}
			{@render grade(onDark ? 'currentColor' : theme.rule)}
		{/if}
	</div>
{/snippet}

{#snippet page()}
	<div
		class="flex h-full flex-col gap-[3.5%] overflow-hidden p-[8%] [container-type:inline-size]"
		style="background:{theme.page};color:{theme.ink}"
	>
		<div class="flex items-center justify-between" style="color:{theme.ink_faint};font-size:5.5cqw">
			<span>2 · Executive summary</span><span>Confidential</span>
		</div>

		<div
			class="flex items-baseline gap-1 pb-[3%]"
			style={theme.heading_style === 'rule'
				? `border-top:1.5px solid ${theme.accent};padding-top:4%`
				: `border-bottom:0.5px solid ${theme.rule}`}
		>
			{#if theme.heading_style === 'numbered'}
				<span class="leading-none" style="color:{theme.accent};font-size:11cqw">2</span>
			{/if}
			<span
				class="truncate leading-none font-semibold"
				style="font-family:{heading};letter-spacing:-0.025em;font-size:11cqw"
			>
				Executive summary
			</span>
		</div>

		<div class="flex items-end gap-[4%]">
			{#each SEV as key, i (key)}
				<div class="flex-1 space-y-[2px]">
					<div style="height:1.5px;background:{theme.severity[key] ?? theme.rule}"></div>
					<div class="leading-none font-semibold" style="font-family:{heading};font-size:8cqw">
						{COUNTS[i]}
					</div>
					<div
						class="truncate leading-none"
						style="color:{theme.ink_faint};text-transform:{caseOf};font-size:5cqw"
					>
						{key}
					</div>
				</div>
			{/each}
		</div>

		<div class="space-y-[3px]" style="font-family:{body}">
			{#each LINES as w, i (i)}
				{@render bar(`${w}%`, theme.ink_soft, '1.5px', 0.8)}
			{/each}
		</div>

		<div>
			<div style="height:0.8px;background:{theme.ink_faint};opacity:.6"></div>
			{#each ROWS as key, row (key)}
				<div
					class="flex items-center gap-[4%] px-[2%] py-[3px]"
					style={theme.table_style === 'zebra' && row % 2 === 1
						? `background:${theme.surface}`
						: `border-bottom:0.5px solid ${theme.rule}`}
				>
					<span
						class="inline-block size-[3px] shrink-0 rounded-full"
						style="background:{theme.severity[key]}"
					></span>
					<div class="flex-1">{@render bar('82%', theme.ink_soft, '1.5px', 0.75)}</div>
					{@render bar('9px', theme.ink_faint, '1.5px', 0.7)}
				</div>
			{/each}
		</div>

		<div class="mt-auto flex justify-between" style="color:{theme.ink_faint};font-size:5.5cqw">
			<span>Security Assessment Report</span><span>5 / 52</span>
		</div>
	</div>
{/snippet}

<div
	class={cn('relative overflow-hidden rounded-md border', className)}
	style="aspect-ratio:{variant === 'spread' ? '1.414/1' : '1/1.414'}"
	aria-hidden="true"
>
	{#if variant === 'spread'}
		<div class="grid h-full grid-cols-2">
			<div class="border-r" style="border-color:{theme.rule}">{@render cover()}</div>
			{@render page()}
		</div>
	{:else if variant === 'cover'}
		{@render cover()}
	{:else}
		{@render page()}
	{/if}
</div>
