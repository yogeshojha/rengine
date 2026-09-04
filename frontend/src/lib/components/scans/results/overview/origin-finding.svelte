<script lang="ts">
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { Badge } from '$lib/components/ui/badge';
	import ScreenshotThumb from '../screenshot-thumb.svelte';
	import TechIcon from '../tech-icon.svelte';
	import {
		FINDING_TITLE,
		frontedLabel,
		networkLabel,
		ORIGIN_EXPOSED,
		type OriginFinding
	} from '$lib/utilities/origins';

	interface Props {
		finding: OriginFinding;
		onOpen: (f: OriginFinding) => void;
	}

	let { finding: f, onOpen }: Props = $props();

	const MAX_PORTS = 6;

	let bypass = $derived(f.kind === ORIGIN_EXPOSED);
	let cdn = $derived(frontedLabel(f));
	let ports = $derived(f.open_ports.slice(0, MAX_PORTS));
	let sensitive = $derived(new Set(f.sensitive_ports));
	let network = $derived(networkLabel(f.exposed));
</script>

<button
	type="button"
	class="group flex w-full flex-col gap-3 border-t border-l p-5 text-left transition-colors hover:bg-muted/30"
	onclick={() => onOpen(f)}
>
	<div class="flex items-start justify-between gap-3">
		<div class="flex min-w-0 flex-col gap-1">
			<span class="flex items-center gap-2">
				<Badge variant={f.confidence === 'high' ? 'warning' : 'outline'} class="font-normal">
					{f.confidence === 'high' ? 'High confidence' : 'Medium confidence'}
				</Badge>
				<span class="text-sm font-medium">{FINDING_TITLE[f.kind] ?? f.kind}</span>
			</span>
			<span class="truncate font-mono text-xs text-muted-foreground">{f.exposed.url}</span>
		</div>
		<ChevronRight
			class="mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5"
		/>
	</div>

	<div class="flex flex-wrap items-stretch gap-3">
		<div class="flex min-w-0 flex-col gap-1.5">
			<span
				class="flex items-center gap-1 text-[11px] tracking-wide text-muted-foreground uppercase"
			>
				{#if bypass}
					<TechIcon name={cdn} class="size-3" /> Behind {cdn}
				{:else}
					By hostname
				{/if}
			</span>
			<ScreenshotThumb
				path={f.fronted[0]?.screenshot_path}
				alt="Response behind the CDN"
				class="h-24 w-40 rounded-md border object-cover"
				interactive={false}
			/>
			<span class="min-w-0 truncate text-xs text-muted-foreground">
				{#if bypass}
					{f.fronted_total}
					{f.fronted_total === 1 ? 'hostname' : 'hostnames'}
				{:else}
					{f.fronted[0]?.host}
				{/if}
			</span>
		</div>

		<div class="flex min-w-0 flex-1 basis-40 flex-col justify-center gap-1.5 px-1">
			<span
				class="flex items-center gap-1.5 text-[11px] tracking-wide text-muted-foreground uppercase"
			>
				Matched on <ArrowRight class="size-3" />
			</span>
			<span class="flex flex-wrap gap-1">
				{#each f.evidence as e (e.kind)}
					<Badge variant="secondary" class="font-normal">{e.label}</Badge>
				{/each}
			</span>
		</div>

		<div class="flex min-w-0 flex-col gap-1.5">
			<span class="text-[11px] tracking-wide text-muted-foreground uppercase">
				Reachable directly
			</span>
			<ScreenshotThumb
				path={f.exposed.screenshot_path}
				alt="Response from the address"
				class="h-24 w-40 rounded-md border object-cover"
				interactive={false}
			/>
			<span class="truncate font-mono text-xs text-muted-foreground">
				{f.exposed.ip}{network ? ` · ${network}` : ''}
			</span>
		</div>
	</div>

	{#if ports.length}
		<span class="flex flex-wrap items-center gap-1">
			{#each ports as p (p)}
				<Badge
					variant="outline"
					class="px-1 font-mono text-[10px] font-normal {sensitive.has(p)
						? 'border-warning/40 text-warning'
						: ''}"
				>
					{p}
				</Badge>
			{/each}
			{#if f.open_ports.length > MAX_PORTS}
				<span class="text-xs text-muted-foreground">+{f.open_ports.length - MAX_PORTS}</span>
			{/if}
			{#if f.sensitive_ports.length}
				<span class="flex items-center gap-1 text-xs text-warning">
					<TriangleAlert class="size-3" />
					{f.sensitive_ports.length} sensitive
				</span>
			{/if}
		</span>
	{/if}
</button>
