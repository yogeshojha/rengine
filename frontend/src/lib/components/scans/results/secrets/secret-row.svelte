<script lang="ts">
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Copy from '@lucide/svelte/icons/copy';
	import Globe from '@lucide/svelte/icons/globe';
	import { toast } from 'svelte-sonner';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import CopyButton from '$lib/components/copy-button.svelte';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import Hint from '$lib/components/hint.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { relativeTime } from '$lib/utilities/dates';
	import { stopProp } from '$lib/utilities';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { STATE_BADGE, STATE_LABELS } from '$lib/config/secrets';
	import type { SecretRead } from '$lib/types/secret';
	import { SECRET_WIDTHS } from './columns';

	interface Props {
		row: SecretRead;
		term?: string;
		selected: boolean;
		checked?: boolean;
		projectWide?: boolean;
		onCheck?: (id: string) => void;
		onOpen: (row: SecretRead) => void;
	}

	let {
		row,
		term = '',
		selected,
		checked = false,
		projectWide = false,
		onCheck,
		onOpen
	}: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];

	let firstLine = $derived(row.value.split('\n')[0]);
	let assetHref = $derived(
		ROUTES.results(WEB.tab, projectWide ? null : row.scan_id, {
			[WEB.queryParam]: `name="${row.host}"`
		})
	);

	async function copyValue() {
		if (await writeClipboard(row.value)) toast.success('Value copied');
	}
</script>

<div
	class="group flex cursor-pointer items-center gap-3 px-4 py-2.5 transition-colors {selected
		? 'bg-primary/5 hover:bg-primary/10'
		: 'hover:bg-muted/30'}"
	onclick={() => onOpen(row)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen(row);
		}
	}}
	role="button"
	tabindex="0"
	aria-label="Open {row.kind_label}"
>
	{#if onCheck}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="hidden shrink-0 sm:flex" onclick={stopProp}>
			<Checkbox
				{checked}
				onCheckedChange={() => onCheck(row.id)}
				aria-label="Select {row.kind_label}"
				class="transition-opacity {checked
					? 'opacity-100'
					: 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100'}"
			/>
		</div>
	{/if}

	<div class="min-w-0 flex-1">
		<div class="flex min-w-0 items-center gap-2">
			<span class="truncate font-mono text-sm">{firstLine}</span>
			<CopyButton
				value={row.value}
				class="shrink-0 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
			/>
		</div>
		<div class="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
			{#if row.is_new}
				<span
					class="inline-flex shrink-0 items-center rounded border border-warning/30 px-1 font-medium text-warning"
				>
					New
				</span>
			{/if}
			<span class="truncate md:hidden">{row.kind_label}</span>
			<span class="hidden truncate md:inline"><HighlightText text={row.url} {term} /></span>
			<span class="text-muted-foreground/40 sm:hidden">·</span>
			<span class="shrink-0 tabular-nums sm:hidden">{relativeTime(row.discovered_at)}</span>
		</div>
	</div>

	{#if projectWide}
		<div class={SECRET_WIDTHS.target}>
			<Hint text={row.target_value ?? ''}>
				{#snippet child(props)}
					<span {...props} class="truncate font-mono text-sm">{row.target_value}</span>
				{/snippet}
			</Hint>
		</div>
	{/if}

	<div class={SECRET_WIDTHS.kind}>
		<span class="truncate text-sm">{row.kind_label}</span>
	</div>

	<div class={SECRET_WIDTHS.state}>
		<Badge variant={STATE_BADGE[row.state] ?? 'outline'}>
			{STATE_LABELS[row.state] ?? row.state}
		</Badge>
	</div>

	<div class={SECRET_WIDTHS.asset}>
		<div class="min-w-0">
			<div class="flex min-w-0 items-center gap-1.5 text-sm">
				<Globe class="size-3.5 shrink-0 text-muted-foreground" />
				<span class="truncate"><HighlightText text={row.host} {term} /></span>
			</div>
			<div class="mt-0.5 truncate pl-5 text-xs text-muted-foreground">
				{#if row.hosts > 1}
					{row.hosts.toLocaleString()} web assets
				{:else}
					{row.source_label}
				{/if}
			</div>
		</div>
	</div>

	<div
		class="{SECRET_WIDTHS.seen} items-center text-right text-xs text-muted-foreground tabular-nums"
	>
		{relativeTime(row.discovered_at)}
	</div>

	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="{SECRET_WIDTHS.actions} items-center" onclick={stopProp}>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="h-8 w-8"
						aria-label="Actions for {row.kind_label}"
					>
						<Ellipsis class="h-4 w-4" />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-44">
				<DropdownMenu.Item onclick={() => onOpen(row)} class="gap-2">
					<ExternalLink class="h-4 w-4" /> Open
				</DropdownMenu.Item>
				<DropdownMenu.Item onclick={copyValue} class="gap-2">
					<Copy class="h-4 w-4" /> Copy value
				</DropdownMenu.Item>
				<DropdownMenu.Separator />
				<DropdownMenu.Item class="gap-2">
					{#snippet child({ props })}
						<a {...props} href={assetHref}>
							<Globe class="h-4 w-4" /> Open web asset
						</a>
					{/snippet}
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
</div>
