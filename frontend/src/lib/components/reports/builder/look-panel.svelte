<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import Hint from '$lib/components/hint.svelte';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import type { ReportStyle } from '$lib/types/report';

	let { style = $bindable() }: { style: ReportStyle } = $props();

	const catalog = $derived(reportCatalog.catalog);
	const textFonts = $derived((catalog?.fonts ?? []).filter((f) => f.role !== 'mono'));
	const monoFonts = $derived((catalog?.fonts ?? []).filter((f) => f.role === 'mono'));
	const activeTheme = $derived(reportCatalog.theme(style.theme));

	const SEVERITIES = ['critical', 'high', 'medium', 'low', 'info'];

	function label(list: { key: string; label: string }[] | undefined, key: string): string {
		return list?.find((i) => i.key === key)?.label ?? key;
	}

	function severity(key: string): string {
		return style.severity_colors[key] ?? activeTheme?.severity[key] ?? '#888888';
	}

	function setSeverity(key: string, value: string) {
		style.severity_colors = { ...style.severity_colors, [key]: value };
	}
</script>

<div class="space-y-6">
	<div class="space-y-2">
		<Label class="text-xs">Theme</Label>
		<div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
			{#each reportCatalog.themes as theme (theme.slug)}
				<button
					type="button"
					class="flex items-center gap-3 rounded-md border p-2.5 text-left transition-colors data-[active=true]:border-primary data-[active=true]:bg-muted"
					data-active={style.theme === theme.slug}
					onclick={() => (style.theme = theme.slug)}
				>
					<span
						class="size-10 shrink-0 overflow-hidden rounded border"
						style="background:{theme.page}"
					>
						<span class="block h-3 w-full" style="background:{theme.accent}"></span>
						<span class="mt-1 ml-1 flex gap-0.5">
							{#each theme.chart.slice(0, 4) as colour, i (i)}
								<span class="size-1.5 rounded-full" style="background:{colour}"></span>
							{/each}
						</span>
					</span>
					<span class="min-w-0">
						<span class="block truncate text-sm font-medium">{theme.name}</span>
						<span class="block truncate text-xs text-muted-foreground">{theme.description}</span>
					</span>
				</button>
			{/each}
		</div>
	</div>

	<Separator />

	<div class="grid gap-4 sm:grid-cols-2">
		<div class="space-y-1.5">
			<Label class="text-xs">Page size</Label>
			<Select.Root type="single" bind:value={style.page_size}>
				<Select.Trigger class="h-9 w-full"
					>{label(catalog?.page_sizes, style.page_size)}</Select.Trigger
				>
				<Select.Content>
					{#each catalog?.page_sizes ?? [] as item (item.key)}
						<Select.Item value={item.key}>{item.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Density</Label>
			<Select.Root type="single" bind:value={style.density}>
				<Select.Trigger class="h-9 w-full"
					>{label(catalog?.densities, style.density)}</Select.Trigger
				>
				<Select.Content>
					{#each catalog?.densities ?? [] as item (item.key)}
						<Select.Item value={item.key}>{item.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Cover layout</Label>
			<Select.Root type="single" bind:value={style.cover_layout}>
				<Select.Trigger class="h-9 w-full">
					{style.cover_layout
						? label(catalog?.cover_layouts, style.cover_layout)
						: 'From the theme'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="">From the theme</Select.Item>
					{#each catalog?.cover_layouts ?? [] as item (item.key)}
						<Select.Item value={item.key}>{item.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Body size</Label>
			<Input
				type="number"
				step="0.5"
				min="6"
				max="16"
				bind:value={style.base_font_size}
				class="h-9"
			/>
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Heading font</Label>
			<Select.Root type="single" bind:value={style.heading_font}>
				<Select.Trigger class="h-9 w-full">
					{style.heading_font
						? (textFonts.find((f) => f.slug === style.heading_font)?.name ?? style.heading_font)
						: 'From the theme'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="">From the theme</Select.Item>
					{#each textFonts as font (font.slug)}
						<Select.Item value={font.slug}>
							{font.name}{#if font.origin === 'custom'}<span
									class="ml-1.5 text-xs text-muted-foreground">yours</span
								>{/if}
						</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Body font</Label>
			<Select.Root type="single" bind:value={style.body_font}>
				<Select.Trigger class="h-9 w-full">
					{style.body_font
						? (textFonts.find((f) => f.slug === style.body_font)?.name ?? style.body_font)
						: 'From the theme'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="">From the theme</Select.Item>
					{#each textFonts as font (font.slug)}
						<Select.Item value={font.slug}>
							{font.name}{#if font.origin === 'custom'}<span
									class="ml-1.5 text-xs text-muted-foreground">yours</span
								>{/if}
						</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Code font</Label>
			<Select.Root type="single" bind:value={style.mono_font}>
				<Select.Trigger class="h-9 w-full">
					{style.mono_font
						? (monoFonts.find((f) => f.slug === style.mono_font)?.name ?? style.mono_font)
						: 'From the theme'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="">From the theme</Select.Item>
					{#each monoFonts as font (font.slug)}
						<Select.Item value={font.slug}>
							{font.name}{#if font.origin === 'custom'}<span
									class="ml-1.5 text-xs text-muted-foreground">yours</span
								>{/if}
						</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
	</div>

	<div class="space-y-2">
		<Label class="text-xs">Margins (mm)</Label>
		<div class="grid grid-cols-4 gap-2">
			{#each [['margin_top', 'Top'], ['margin_right', 'Right'], ['margin_bottom', 'Bottom'], ['margin_left', 'Left']] as [key, name] (key)}
				<div class="space-y-1">
					<span class="text-[11px] text-muted-foreground">{name}</span>
					<Input
						type="number"
						min="5"
						max="60"
						value={style[key as keyof ReportStyle] as number}
						class="h-9"
						oninput={(e) =>
							((style as unknown as Record<string, number>)[key] = Number(e.currentTarget.value))}
					/>
				</div>
			{/each}
		</div>
	</div>

	<Separator />

	<div class="space-y-3">
		<Label class="text-xs">Colours</Label>
		<div class="flex flex-wrap items-center gap-3">
			<div class="flex items-center gap-2">
				<input
					type="color"
					class="size-8 cursor-pointer rounded border bg-transparent"
					value={style.accent || activeTheme?.accent || '#4f46e5'}
					oninput={(e) => (style.accent = e.currentTarget.value)}
					aria-label="Accent colour"
				/>
				<span class="text-xs text-muted-foreground">Accent</span>
			</div>
			{#each SEVERITIES as key (key)}
				<div class="flex items-center gap-2">
					<input
						type="color"
						class="size-8 cursor-pointer rounded border bg-transparent"
						value={severity(key)}
						oninput={(e) => setSeverity(key, e.currentTarget.value)}
						aria-label={`${key} colour`}
					/>
					<span class="text-xs capitalize text-muted-foreground">{key}</span>
				</div>
			{/each}
			{#if style.accent || Object.keys(style.severity_colors).length}
				<Button
					variant="ghost"
					size="sm"
					class="h-7 text-xs"
					onclick={() => {
						style.accent = '';
						style.severity_colors = {};
					}}
				>
					Back to the theme
				</Button>
			{/if}
		</div>
	</div>

	<Separator />

	<div class="space-y-3">
		<div class="flex items-center justify-between">
			<Label class="text-xs">Running header and footer</Label>
			<Popover.Root>
				<Popover.Trigger>
					{#snippet child({ props })}
						<Button variant="ghost" size="sm" class="h-7 text-xs" {...props}>
							What can go in a slot?
						</Button>
					{/snippet}
				</Popover.Trigger>
				<Popover.Content class="w-72">
					<p class="mb-2 text-xs text-muted-foreground">
						Type any text. These tokens are replaced when the document is laid out.
					</p>
					<div class="grid grid-cols-2 gap-1 text-xs">
						{#each catalog?.slot_tokens ?? [] as token (token.token)}
							<code class="font-mono">{token.token}</code>
							<span class="text-muted-foreground">{token.label}</span>
						{/each}
					</div>
				</Popover.Content>
			</Popover.Root>
		</div>

		<div class="flex items-center justify-between">
			<span class="text-sm">Show the header</span>
			<Switch checked={style.show_header} onCheckedChange={(v) => (style.show_header = v)} />
		</div>
		{#if style.show_header}
			<div class="grid grid-cols-3 gap-2">
				<Input bind:value={style.header_left} placeholder="Left" class="h-9 font-mono text-xs" />
				<Input
					bind:value={style.header_center}
					placeholder="Centre"
					class="h-9 font-mono text-xs"
				/>
				<Input bind:value={style.header_right} placeholder="Right" class="h-9 font-mono text-xs" />
			</div>
		{/if}

		<div class="flex items-center justify-between">
			<span class="text-sm">Show the footer</span>
			<Switch checked={style.show_footer} onCheckedChange={(v) => (style.show_footer = v)} />
		</div>
		{#if style.show_footer}
			<div class="grid grid-cols-3 gap-2">
				<Input bind:value={style.footer_left} placeholder="Left" class="h-9 font-mono text-xs" />
				<Input
					bind:value={style.footer_center}
					placeholder="Centre"
					class="h-9 font-mono text-xs"
				/>
				<Input bind:value={style.footer_right} placeholder="Right" class="h-9 font-mono text-xs" />
			</div>
		{/if}
	</div>

	<Separator />

	<div class="space-y-3">
		{#each [['section_numbering', 'Number the sections', 'Prints 1., 2., 3. before each heading.'], ['table_zebra', 'Shade alternate table rows', ''], ['mono_safe', 'Ink saving', 'Greys every fill so the document prints cleanly in black and white.'], ['hyphenate', 'Hyphenate body text', 'Tighter paragraphs, at the cost of more broken words.']] as [key, name, help] (key)}
			<div class="flex items-start justify-between gap-4">
				<div class="space-y-0.5">
					<span class="text-sm">{name}</span>
					{#if help}<p class="text-xs text-muted-foreground">{help}</p>{/if}
				</div>
				<Switch
					checked={Boolean((style as unknown as Record<string, boolean>)[key])}
					onCheckedChange={(v) => ((style as unknown as Record<string, boolean>)[key] = v)}
				/>
			</div>
		{/each}
	</div>

	<Separator />

	<div class="grid gap-4 sm:grid-cols-2">
		<div class="space-y-1.5">
			<Hint text="Printed diagonally behind every page.">
				{#snippet child(props)}
					<span class="inline-flex" {...props}><Label class="text-xs">Watermark</Label></span>
				{/snippet}
			</Hint>
			<Input bind:value={style.watermark_text} placeholder="DRAFT" class="h-9" />
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Watermark strength</Label>
			<Input
				type="number"
				step="0.01"
				min="0.01"
				max="0.4"
				bind:value={style.watermark_opacity}
				class="h-9"
			/>
		</div>
	</div>
</div>
