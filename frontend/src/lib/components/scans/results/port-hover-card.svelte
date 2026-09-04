<script lang="ts">
	import { untrack, type Snippet } from 'svelte';
	import Lock from '@lucide/svelte/icons/lock';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ServiceIcon from './services/service-icon.svelte';
	import { screenshotUrl } from '$lib/utilities/media';
	import { claimHover, releaseHover } from '$lib/utilities/hover-exclusive';
	import {
		httpStatusClass,
		httpStatusReason,
		isSensitivePort,
		STATUS_DOT
	} from '$lib/utilities/scan-correlation';
	import { serviceLabel, type ServiceRead } from '$lib/utilities/services';
	import {
		PORT_SOURCE_HELP,
		PORT_SOURCE_LABELS,
		serviceClassLabel
	} from '$lib/config/service-classes';

	interface Props {
		port: number;
		load: () => Promise<ServiceRead[]>;
		address?: string;
		onServices?: (port: number) => void;
		children: Snippet;
	}

	let { port, load, address = '', onServices, children }: Props = $props();

	const MAX_ADDRESSES = 4;

	let open = $state(false);
	let rows = $state<ServiceRead[] | null>(null);
	let errored = $state(false);
	let shot = $state<string | null>(null);
	let requested = false;

	let named = $derived((rows ?? []).filter((r) => r.product || r.service_name));
	let lead = $derived(named[0] ?? rows?.[0] ?? null);
	let addresses = $derived(rows ?? []);
	let http = $derived(addresses.find((r) => r.status_code) ?? null);
	let shotAlt = $derived(`Screenshot of ${http?.url ?? `port ${port}`}`);
	let sensitive = $derived(lead?.is_sensitive ?? isSensitivePort(port));
	let tls = $derived(addresses.some((r) => r.tls));
	let source = $derived(lead?.source ?? '');
	let help = $derived(addresses.length === 1 ? (PORT_SOURCE_HELP[source] ?? '') : '');

	$effect(() => {
		const url = screenshotUrl(http?.screenshot_path);
		if (!url) {
			shot = null;
			return;
		}
		let alive = true;
		const probe = new Image();
		probe.onload = () => {
			if (alive) shot = url;
		};
		probe.src = url;
		return () => {
			alive = false;
		};
	});

	const closeSelf = () => (open = false);
	$effect(() => {
		if (open) claimHover(closeSelf);
		else releaseHover(closeSelf);
	});

	$effect(() => {
		if (!open) return;
		untrack(() => {
			if (requested) return;
			requested = true;
			load()
				.then((list) => (rows = list.filter((r) => r.port === port)))
				.catch(() => (errored = true));
		});
	});
</script>

<HoverCard.Root bind:open openDelay={320} closeDelay={120}>
	<HoverCard.Trigger>
		{#snippet child({ props })}
			<span {...props} class="inline-flex">{@render children()}</span>
		{/snippet}
	</HoverCard.Trigger>
	<HoverCard.Content side="top" align="start" class="mt-0 w-80 overflow-hidden p-0">
		{#if shot}
			<img
				src={shot}
				alt={shotAlt}
				class="aspect-video w-full border-b border-border bg-muted object-cover object-top"
			/>
		{/if}
		<div class="flex items-center gap-2 border-b border-border px-3 py-2">
			<ServiceIcon
				service={lead?.service_name ?? null}
				serviceClass={lead?.service_class ?? ''}
				product={lead?.product}
				class="size-4 shrink-0"
			/>
			<span class="font-mono text-sm font-medium">{port}/{lead?.protocol ?? 'tcp'}</span>
			{#if lead}
				<span class="truncate text-xs text-muted-foreground">
					{lead.service_name ?? serviceClassLabel(lead.service_class)}
				</span>
			{/if}
			<div class="ml-auto flex shrink-0 items-center gap-1">
				{#if tls}
					<Lock class="size-3 text-muted-foreground" />
				{/if}
				{#if sensitive}
					<Badge variant="warning" class="px-1 text-[10px] font-normal">Sensitive</Badge>
				{/if}
			</div>
		</div>

		<div class="flex flex-col gap-2 p-3 text-xs">
			{#if errored}
				<p class="text-muted-foreground">Service details could not be loaded.</p>
			{:else if rows === null}
				<Skeleton class="h-3 w-full" />
				<Skeleton class="h-3 w-4/5" />
				<Skeleton class="h-3 w-2/3" />
			{:else if !addresses.length}
				<p class="text-muted-foreground">No service recorded on this port.</p>
			{:else}
				{#if lead?.description}
					<p class="leading-snug">{lead.description}</p>
					{#if lead.registered}
						<p class="text-muted-foreground">
							IANA registration for port {port}. Not confirmed by this scan.
						</p>
					{/if}
				{:else}
					<p class="text-muted-foreground">Service not identified.</p>
				{/if}

				{#if http}
					<div class="flex items-center gap-2">
						<span class="size-2 rounded-full {STATUS_DOT[httpStatusClass(http.status_code)]}"
						></span>
						<span class="font-mono font-medium">{http.status_code}</span>
						<span class="truncate text-muted-foreground">
							{http.title || httpStatusReason(http.status_code)}
						</span>
					</div>
				{/if}

				<div class="flex flex-col gap-1 border-t border-border pt-2">
					{#each addresses.slice(0, MAX_ADDRESSES) as r (r.id)}
						<div class="flex items-baseline gap-2">
							{#if r.ip === address}
								<span class="truncate text-muted-foreground">
									{r.product ? serviceLabel(r) : 'Not identified'}
								</span>
							{:else}
								<span class="truncate font-mono">{r.ip}</span>
								{#if r.product}
									<span class="truncate text-muted-foreground">{serviceLabel(r)}</span>
								{/if}
							{/if}
							<span class="ml-auto shrink-0 text-[11px] text-muted-foreground">
								{PORT_SOURCE_LABELS[r.source] ?? r.source}
							</span>
						</div>
					{/each}
					{#if addresses.length > MAX_ADDRESSES}
						<p class="text-[11px] text-muted-foreground">
							+{addresses.length - MAX_ADDRESSES} addresses
						</p>
					{/if}
					{#if help}
						<p class="text-[11px] text-muted-foreground">{help}</p>
					{/if}
				</div>

				{#if onServices}
					<Button
						variant="ghost"
						size="sm"
						class="-mb-1 h-7 justify-start px-1 text-xs"
						onclick={() => {
							open = false;
							onServices(port);
						}}
					>
						{addresses.length} in Services
						<ChevronRight class="size-3.5" />
					</Button>
				{/if}
			{/if}
		</div>
	</HoverCard.Content>
</HoverCard.Root>
