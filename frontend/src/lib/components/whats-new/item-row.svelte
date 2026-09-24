<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import CopyButton from '$lib/components/copy-button.svelte';
	import BellOff from '@lucide/svelte/icons/bell-off';
	import Bell from '@lucide/svelte/icons/bell';
	import Check from '@lucide/svelte/icons/check';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ScreenshotThumb from '$lib/components/scans/results/screenshot-thumb.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { NewKind, TERMS_KINDS } from '$lib/config/whats-new';
	import { rowHref } from '$lib/utilities/whats-new';
	import type { NewItem } from '$lib/types/whats-new';

	interface Props {
		item: NewItem;
		checked?: boolean;
		selectable?: boolean;
		busy?: boolean;
		sheet?: boolean;
		onOpen?: (item: NewItem) => void;
		onCheck?: (item: NewItem, shift: boolean) => void;
		onAddTarget?: (item: NewItem) => void;
		onWatch?: (item: NewItem) => void;
		onMute?: (item: NewItem) => void;
		onScan?: (item: NewItem) => void;
		onRemoveTarget?: (item: NewItem) => void;
	}

	let {
		item,
		checked = false,
		selectable = false,
		busy = false,
		sheet = false,
		onOpen,
		onCheck,
		onAddTarget,
		onWatch,
		onMute,
		onScan,
		onRemoveTarget
	}: Props = $props();

	const MONO_KINDS = new Set<string>([
		NewKind.SCOPE,
		NewKind.CERT_HOST,
		NewKind.TARGET,
		NewKind.OUT_OF_SCOPE
	]);

	let link = $derived(rowHref(item));
	let shift = false;
	let mono = $derived(MONO_KINDS.has(item.kind));
	let answer = $derived(
		item.status === null ? null : `${item.status}${item.title ? ` · ${item.title}` : ''}`
	);
	let programHref = $derived(
		item.handle ? ROUTES.bountyHub(item.handle, item.platform ?? undefined) : null
	);
</script>

<div
	class="group/row grid grid-cols-[1.25rem_minmax(0,1fr)_auto] items-center gap-x-3 px-3 py-1.5 transition-colors hover:bg-muted/50 max-sm:grid-cols-[1.25rem_minmax(0,1fr)]"
>
	<div class="flex h-5 items-center">
		{#if selectable}
			<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
			<span onclickcapture={(e) => (shift = e.shiftKey)}>
				<Checkbox
					{checked}
					aria-label="Select {item.value}"
					onCheckedChange={() => onCheck?.(item, shift)}
					class="size-3.5"
				/>
			</span>
		{/if}
	</div>

	<div class="flex min-w-0 items-center gap-3">
		{#if item.screenshot_path}
			<ScreenshotThumb
				path={item.screenshot_path}
				alt={item.value}
				class="h-7 w-11 shrink-0"
				preview
			/>
		{/if}
		<div class="flex min-w-0 flex-wrap items-baseline gap-x-2.5 gap-y-0.5">
			{#if sheet}
				<button
					type="button"
					class="min-w-0 text-left text-sm wrap-anywhere hover:text-primary {mono
						? 'font-mono text-sm'
						: 'font-medium'}"
					onclick={(e) => {
						e.stopPropagation();
						onOpen?.(item);
					}}
				>
					{item.value}
				</button>
				{#if link}
					<a
						href={link}
						class="inline-flex text-muted-foreground opacity-0 group-hover/row:opacity-100 hover:text-foreground focus-visible:opacity-100"
						aria-label="Open in the scan"
					>
						<ArrowUpRight class="size-3.5" />
					</a>
				{/if}
			{:else if link}
				<a
					href={link}
					class="inline-flex min-w-0 items-center gap-1 text-sm wrap-anywhere hover:text-primary {mono
						? 'font-mono text-sm'
						: 'font-medium'}"
				>
					{item.value}
					<ArrowUpRight
						class="size-3 shrink-0 text-muted-foreground opacity-0 group-hover/row:opacity-100"
					/>
				</a>
			{:else}
				<span class="text-sm wrap-anywhere {mono ? 'font-mono text-sm' : 'font-medium'}">
					{item.value}
				</span>
			{/if}

			{#if TERMS_KINDS.has(item.kind)}
				{#if item.asset_type}<span class="text-xs text-muted-foreground">{item.asset_type}</span
					>{/if}
				{#if item.detail}<span class="text-xs wrap-anywhere">{item.detail}</span>{/if}
			{:else if item.kind === NewKind.CERT_HOST}
				<span class="text-xs text-muted-foreground">
					{#if answer}<span class="text-foreground">{answer}</span
						>{:else if item.ips.length === 0}Unresolved{/if}
					{#if item.tech.length}<span> · {item.tech.join(', ')}</span>{/if}
					{#if item.ips.length}<span class="font-mono"> · {item.ips.join(', ')}</span>{/if}
					{#if item.detail}<span> · {item.detail}</span>{/if}
				</span>
				{#if item.muted}<Badge variant="secondary">Muted</Badge>{/if}
			{:else if item.kind === NewKind.SCOPE || item.kind === NewKind.OUT_OF_SCOPE}
				{#if item.kind === NewKind.OUT_OF_SCOPE}
					<Badge variant="destructive">{item.detail ?? 'Out of scope'}</Badge>
				{/if}
				{#if item.asset_type}<span class="text-xs text-muted-foreground">{item.asset_type}</span
					>{/if}
				{#if item.target_exists && item.target_id}
					<a href={ROUTES.target(item.target_id)} class="inline-flex">
						<Badge variant="success" class="gap-1"><Check class="size-3" /> Target</Badge>
					</a>
				{/if}
			{:else if item.kind === NewKind.PROGRAM}
				{#if item.detail}<span class="text-xs text-muted-foreground">{item.detail}</span>{/if}
				{#if item.watch_id}<Badge variant="info">Watched</Badge>{/if}
			{:else if item.kind === NewKind.TARGET}
				{#if item.detail && programHref}
					<a href={programHref} class="text-xs text-muted-foreground hover:text-foreground"
						>{item.detail}</a
					>
				{/if}
				<span class="text-xs text-muted-foreground">{item.scanned ? 'Scanned' : 'Not scanned'}</span
				>
			{/if}
		</div>
	</div>

	<div
		class="flex items-center justify-end gap-0.5 opacity-40 transition-opacity group-hover/row:opacity-100 focus-within:opacity-100 max-sm:col-start-2 max-sm:justify-start max-sm:opacity-100"
	>
		{#if mono}
			<CopyButton
				value={item.value}
				class="size-7 opacity-0 group-hover/row:opacity-100 focus-visible:opacity-100"
			/>
		{/if}
		{#if item.kind === NewKind.SCOPE && item.importable && !item.target_exists}
			<LoadingButton
				size="sm"
				class="h-7 px-2.5 text-xs"
				loading={busy}
				loadingLabel="Adding"
				onclick={() => onAddTarget?.(item)}
			>
				Add target
			</LoadingButton>
			{#if !item.watch_id}
				<Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={() => onWatch?.(item)}
					>Watch</Button
				>
			{/if}
		{:else if item.kind === NewKind.SCOPE && item.target_exists && item.target_id}
			<Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={() => onScan?.(item)}>
				{item.scanned ? 'Scan' : 'Scan now'}
			</Button>
		{:else if item.kind === NewKind.PROGRAM}
			{#if !item.watch_id}
				<Button
					variant="outline"
					size="sm"
					class="h-7 px-2.5 text-xs"
					onclick={() => onWatch?.(item)}>Watch</Button
				>
			{/if}
			{#if programHref}
				<Button variant="ghost" size="sm" class="h-7 px-2 text-xs" href={programHref}>Scope</Button>
			{/if}
			{#if item.program_url}
				<Hint text="Open on {item.platform}">
					{#snippet child(props)}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7"
							href={item.program_url}
							target="_blank"
							rel="noreferrer"
							aria-label="Open on the platform"
						>
							<ExternalLink class="size-3.5" />
						</Button>
					{/snippet}
				</Hint>
			{/if}
		{:else if item.kind === NewKind.CERT_HOST}
			{#if item.scan_id}
				<Button variant="ghost" size="sm" class="h-7 px-2 text-xs" href={ROUTES.scan(item.scan_id)}
					>Probe</Button
				>
			{/if}
			<Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={() => onScan?.(item)}
				>Scan</Button
			>
			<Hint text={item.muted ? 'Alerts resume for this host' : 'No further alerts for this host'}>
				{#snippet child(props)}
					<LoadingButton
						{...props}
						variant="ghost"
						size="icon"
						class="size-7"
						loading={busy}
						aria-label={item.muted ? 'Unmute' : 'Mute'}
						onclick={() => onMute?.(item)}
					>
						{#if item.muted}<Bell class="size-3.5" />{:else}<BellOff class="size-3.5" />{/if}
					</LoadingButton>
				{/snippet}
			</Hint>
		{:else if item.kind === NewKind.TARGET}
			<Button
				size="sm"
				variant={item.scanned ? 'ghost' : 'default'}
				class="h-7 px-2.5 text-xs"
				onclick={() => onScan?.(item)}
			>
				{item.scanned ? 'Scan' : 'Scan now'}
			</Button>
		{:else if item.kind === NewKind.OUT_OF_SCOPE}
			{#if item.target_exists && item.target_id}
				<LoadingButton
					variant="ghost"
					size="sm"
					class="h-7 px-2 text-xs text-destructive hover:text-destructive"
					loading={busy}
					loadingLabel="Removing"
					onclick={() => onRemoveTarget?.(item)}
				>
					Remove target
				</LoadingButton>
			{/if}
		{/if}
	</div>
</div>
