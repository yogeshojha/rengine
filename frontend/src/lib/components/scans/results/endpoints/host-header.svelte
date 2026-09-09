<script lang="ts">
	import Globe from '@lucide/svelte/icons/globe';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Copy from '@lucide/svelte/icons/copy';
	import ListOrdered from '@lucide/svelte/icons/list-ordered';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import Layers from '@lucide/svelte/icons/layers';

	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import TechIcon from '../tech-icon.svelte';
	import ProxySend from './proxy-send.svelte';
	import {
		INTEREST_HELP,
		INTEREST_LABELS,
		INTEREST_TONE,
		STATUS_CLASS_FILL,
		statusClassOf
	} from '$lib/config/endpoints';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { HostBrief, ParamStat } from '$lib/utilities/endpoints';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

	interface Props {
		host: string;
		brief: HostBrief | null;
		loading?: boolean;
		connectors?: Connector[];
		catalog?: ConnectorSpec[];
		onPivot: (token: string) => void;
		onNew: () => void;
		onFindings?: () => void;
		onWebAsset?: () => void;
		onCopy: () => void;
		onWordlist: () => void;
		onVerify?: () => void;
		onSend?: (connectorId: string) => Promise<void> | void;
		onAcross: () => void;
	}

	let {
		host,
		brief,
		loading = false,
		connectors = [],
		catalog = [],
		onPivot,
		onNew,
		onFindings,
		onWebAsset,
		onCopy,
		onWordlist,
		onVerify,
		onSend,
		onAcross
	}: Props = $props();

	const PARAM_LIMIT = 12;
	let allParams = $state(false);

	let identity = $derived(brief?.identity ?? null);
	let firstTech = $derived(identity?.tech[0] ?? '');
	let statusClass = $derived(statusClassOf(identity?.status_code));
	let shownParams = $derived(
		allParams ? (brief?.params ?? []) : (brief?.params ?? []).slice(0, PARAM_LIMIT)
	);
	let hiddenParams = $derived(Math.max(0, (brief?.params_total ?? 0) - shownParams.length));
	let unchecked = $derived(brief ? Math.max(0, brief.total - brief.probed) : 0);
	let openUrl = $derived(`https://${host}/`);

	const n = (v: number) => v.toLocaleString();

	function paramClass(p: ParamStat): string {
		if (!p.interest) return 'border-border/70 bg-muted/40';
		return INTEREST_TONE[p.interest] === 'destructive'
			? 'border-destructive/40 bg-destructive/5'
			: 'border-warning/45 bg-warning/10';
	}
	function paramHint(p: ParamStat): string {
		const where = `On ${n(p.count)} ${p.count === 1 ? 'endpoint' : 'endpoints'}.`;
		if (!p.interest) return where;
		return `${INTEREST_LABELS[p.interest] ?? p.interest}. ${INTEREST_HELP[p.interest] ?? ''} ${where}`;
	}
</script>

<div class="flex flex-col gap-3 border-b px-4 py-3">
	<div class="flex flex-wrap items-center gap-x-3 gap-y-2">
		<div class="flex min-w-0 flex-1 basis-72 items-center gap-2.5">
			<span class="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted/60">
				<TechIcon name={firstTech} class="size-4">
					{#snippet fallback()}
						<Globe class="size-4 text-muted-foreground" />
					{/snippet}
				</TechIcon>
			</span>
			<span class="min-w-0 font-mono text-base font-semibold break-all">{host}</span>
			{#if identity?.status_code !== null && identity?.status_code !== undefined}
				<span class="flex h-5 shrink-0 items-center gap-1.5">
					<span class="size-1.5 rounded-full" style="background:{STATUS_CLASS_FILL[statusClass]}"
					></span>
					<span class="font-mono text-xs tabular-nums">{identity.status_code}</span>
				</span>
			{/if}
			{#if identity?.title}
				<span class="min-w-0 truncate text-sm text-muted-foreground">
					{identity.title}
				</span>
			{/if}
		</div>
		<div class="flex shrink-0 items-center gap-1.5">
			<Button
				variant="outline"
				size="sm"
				class="h-8 gap-1.5 text-xs"
				href={openUrl}
				target="_blank"
				rel="noopener noreferrer"
			>
				<ExternalLink class="size-3" /> Open
			</Button>
			{#if onWebAsset}
				<Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs" onclick={onWebAsset}>
					<Globe class="size-3" /> Web asset
				</Button>
			{/if}
		</div>
	</div>

	{#if loading && !brief}
		<Skeleton class="h-5 w-3/4" />
		<Skeleton class="h-5 w-1/2" />
	{:else if brief}
		<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
			<span
				><b class="font-semibold text-foreground tabular-nums">{n(brief.total)}</b> endpoints</span
			>
			{#if brief.probed}
				<button type="button" class="hover:underline" onclick={() => onPivot('is:probed')}>
					<b class="font-semibold text-foreground tabular-nums">{n(brief.probed)}</b> verified
				</button>
			{/if}
			{#if brief.with_params}
				<button type="button" class="hover:underline" onclick={() => onPivot('is:param')}>
					<b class="font-semibold text-foreground tabular-nums">{n(brief.with_params)}</b> take input
				</button>
			{/if}
			{#if brief.api}
				<button type="button" class="hover:underline" onclick={() => onPivot('class:api')}>
					<b class="font-semibold text-foreground tabular-nums">{n(brief.api)}</b> API
				</button>
			{/if}
			{#if brief.walled}
				<button type="button" class="hover:underline" onclick={() => onPivot('is:auth')}>
					<b class="font-semibold text-foreground tabular-nums">{n(brief.walled)}</b> behind auth
				</button>
			{/if}
			{#if brief.new}
				<button type="button" class="hover:underline" onclick={onNew}>
					<b class="font-semibold text-success tabular-nums">+{n(brief.new)}</b>
					new{#if brief.previous_scan_at}
						since {formatShortDate(brief.previous_scan_at)}{/if}
				</button>
			{/if}
			{#if brief.findings && onFindings}
				<button type="button" class="hover:underline" onclick={onFindings}>
					<b class="font-semibold text-destructive tabular-nums">{n(brief.findings)}</b>
					{brief.findings === 1 ? 'finding' : 'findings'}
				</button>
			{/if}
		</div>

		{#if brief.params.length}
			<div class="flex flex-wrap items-center gap-1">
				<span class="mr-1 text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
					Parameters
				</span>
				{#each shownParams as p (p.name)}
					<Hint text={paramHint(p)}>
						{#snippet child(props)}
							<button
								{...props}
								type="button"
								class="inline-flex h-5 items-center gap-1 rounded border px-1.5 font-mono text-[11px] leading-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {paramClass(
									p
								)}"
								onclick={() => onPivot(`param:${p.name}`)}
							>
								{p.name}
								<span class="font-sans tabular-nums text-muted-foreground">{n(p.count)}</span>
							</button>
						{/snippet}
					</Hint>
				{/each}
				{#if hiddenParams > 0}
					<button
						type="button"
						class="text-[11px] text-muted-foreground hover:text-foreground hover:underline"
						onclick={() => (allParams = true)}
					>
						+{n(hiddenParams)} more
					</button>
				{:else if allParams && brief.params_total > PARAM_LIMIT}
					<button
						type="button"
						class="text-[11px] text-muted-foreground hover:text-foreground hover:underline"
						onclick={() => (allParams = false)}
					>
						Show fewer
					</button>
				{/if}
			</div>
		{/if}

		<div class="flex flex-wrap items-center gap-1.5">
			<Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs" onclick={onCopy}>
				<Copy class="size-3" /> Copy {n(brief.total)} URLs
			</Button>
			<Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs" onclick={onWordlist}>
				<ListOrdered class="size-3" /> Copy as wordlist
			</Button>
			{#if onVerify && unchecked > 0}
				<Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs" onclick={onVerify}>
					<ShieldCheck class="size-3" /> Verify {n(unchecked)} unchecked
				</Button>
			{/if}
			{#if onSend && connectors.length}
				<ProxySend {connectors} {catalog} {onSend} />
			{/if}
			<Button variant="ghost" size="sm" class="h-8 gap-1.5 text-xs" onclick={onAcross}>
				<Layers class="size-3" /> See paths across hosts
			</Button>
		</div>
	{/if}
</div>
