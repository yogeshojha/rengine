<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Star from '@lucide/svelte/icons/star';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Copy from '@lucide/svelte/icons/copy';
	import Link from '@lucide/svelte/icons/link';
	import Filter from '@lucide/svelte/icons/filter';
	import CornerDownRight from '@lucide/svelte/icons/corner-down-right';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import Lock from '@lucide/svelte/icons/lock';
	import Network from '@lucide/svelte/icons/network';
	import ShieldX from '@lucide/svelte/icons/shield-x';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Flame from '@lucide/svelte/icons/flame';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import MatchChips from './match-chips.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import OverflowPopover from '../table/overflow-popover.svelte';
	import HostHoverCard from './host-hover-card.svelte';
	import SamePagePopover from './same-page-popover.svelte';
	import PortHoverCard from '../port-hover-card.svelte';
	import PortOverflow from '../port-overflow.svelte';
	import ScreenshotThumb from '../screenshot-thumb.svelte';
	import TechIcon from '../tech-icon.svelte';
	import {
		providerFor,
		PROVIDER_KIND_ICONS,
		PROVIDER_KIND_LABELS
	} from '$lib/config/hosting-providers';
	import { stopProp } from '$lib/utilities';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import {
		formatBytes,
		formatResponseTime,
		httpStatusClass,
		httpStatusReason,
		httpStatusTextClass,
		isPrivateIp,
		isSensitivePort,
		STATUS_DOT
	} from '$lib/utilities/scan-correlation';
	import {
		certState,
		daysUntilExpiry,
		exactToken,
		filterToken
	} from '$lib/utilities/scan-insights';
	import { SEVERITY_FILL, severityLabel } from '$lib/config/vulnerabilities';
	import type { IconComponent } from '$lib/config/icons';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import type { ServiceRead } from '$lib/utilities/services';
	import { ACTIONS_BODY, ACTIONS_PIN, pinTone, rowTone, type TableColumn } from '../table/columns';

	interface Props {
		sub: SubdomainRead;
		index: number;
		apex?: string;
		columns: TableColumn[];
		checked: boolean;
		onCheck: (id: string) => void;
		selected: boolean;
		focused: boolean;
		pad: string;
		onOpen: (s: SubdomainRead) => void;
		onHost: (name: string) => void;
		onFilter: (token: string) => void;
		onEvidence: (sub: SubdomainRead, field: string) => void;
		hostsWithTitle: (title: string) => Promise<string[]>;
		loadServices: (host: string) => Promise<ServiceRead[]>;
		onServices?: (host: string, port: number) => void;
		onVulns?: (filter: string) => void;
	}

	let {
		sub: s,
		index,
		apex = '',
		columns,
		checked,
		onCheck,
		selected,
		focused,
		pad,
		onOpen,
		onHost,
		onFilter,
		onEvidence,
		hostsWithTitle,
		loadServices,
		onServices,
		onVulns
	}: Props = $props();

	let worstSeverity = $derived((s.vuln_count ?? 0) > 0 ? (s.vuln_severity ?? null) : null);

	const ALWAYS_VISIBLE = ['host', 'title', 'cname'];
	const COLUMN_EVIDENCE: Record<string, string> = {
		tech: 'tech',
		ip: 'ip',
		sources: 'source'
	};

	const MAX_TECH = 3;
	const MAX_IPS = 2;
	const MAX_PORTS = 4;
	const MAX_SOURCES = 2;
	const AUTH_CODES = new Set([401, 403]);

	let apexSuffix = $derived(
		apex && s.name !== apex && s.name.endsWith(`.${apex}`) ? `.${apex}` : ''
	);
	let headLabels = $derived((apexSuffix ? s.name.slice(0, -apexSuffix.length) : s.name).split('.'));
	let cert = $derived(certState(s));
	let ports = $derived(s.ports ?? []);
	let ips = $derived(s.resolved_ips ?? []);
	let internalIp = $derived(ips.find(isPrivateIp) ?? null);
	let redirected = $derived(!!s.final_url && s.final_url !== s.http_url);
	let provider = $derived(providerFor(s.cname));
	let expiry = $derived(s.tls_not_after ? formatShortDate(s.tls_not_after) : null);
	let certIssue = $derived(cert === 'expired' || cert === 'expiring' || cert === 'self-signed');
	let signals = $derived(certIssue || !!s.waf || !!internalIp);
	let cnameToken = $derived(s.cname ? filterToken('cname', s.cname) : '');
	let faviconToken = $derived(s.favicon_hash ? filterToken('favicon', s.favicon_hash) : '');
	let matches = $derived(s.matched_in ?? []);
	let titleTerm = $derived(matches.find((m) => m.field === 'title')?.term ?? '');
	let suppressed = $derived(
		new Set([
			...ALWAYS_VISIBLE,
			...columns.map((c) => COLUMN_EVIDENCE[c.key]).filter((v): v is string => !!v)
		])
	);
	let statusCls = $derived(httpStatusClass(s.http_status));
	let tone = $derived(rowTone(selected || checked, focused));
	let pin = $derived(pinTone(selected || checked, focused));

	function pivot(e: Event, token: string) {
		stopProp(e);
		onFilter(token);
	}
	async function copy(text: string) {
		if (await writeClipboard(text)) toast.success('Copied');
	}
</script>

{#snippet signal(label: string, tip: string, token: string, cls: string, Icon: IconComponent)}
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				<button
					{...props}
					type="button"
					class="inline-flex items-center gap-1 rounded border px-1.5 py-px text-xs font-medium {cls}"
					onclick={(e) => pivot(e, token)}
				>
					<Icon class="size-3" />
					{label}
				</button>
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content>{tip}</Tooltip.Content>
	</Tooltip.Root>
{/snippet}

{#snippet title(clamp: string)}
	{#if s.page_title}
		<Hint text={s.page_title}>
			{#snippet child(props)}
				<span {...props} class="min-w-0 wrap-anywhere text-foreground/80 {clamp}">
					<HighlightText text={s.page_title ?? ''} term={titleTerm} />
				</span>
			{/snippet}
		</Hint>
		{#if (s.title_count ?? 0) > 1}
			{@const pageTitle = s.page_title}
			<SamePagePopover
				count={s.title_count ?? 0}
				title="{s.title_count} hosts show “{pageTitle}”"
				load={() => hostsWithTitle(pageTitle)}
				{onHost}
				onFilter={() => onFilter(exactToken('title', pageTitle))}
				class="flex h-4 items-center"
			/>
		{/if}
	{:else if s.http_status}
		<span class="italic">No page title</span>
	{:else}
		<span>—</span>
	{/if}
{/snippet}

<div
	class="group flex cursor-pointer items-center gap-3 px-4 transition-colors {pad} {tone}"
	role="button"
	tabindex={0}
	data-row-index={index}
	aria-label="Open {s.name}"
	onclick={() => onOpen(s)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen(s);
		}
	}}
>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="hidden shrink-0 sm:flex" onclick={stopProp}>
		<Checkbox
			{checked}
			onCheckedChange={() => onCheck(s.id)}
			aria-label="Select {s.name}"
			class="transition-opacity {checked
				? 'opacity-100'
				: 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100'}"
		/>
	</div>

	<div class="flex min-w-0 flex-[3] flex-col gap-1 contain-inline-size sm:min-w-56">
		<div class="flex items-start gap-1.5">
			{#if s.is_important}
				<span class="flex h-5 shrink-0 items-center">
					<Star class="size-3 fill-warning text-warning" />
				</span>
			{/if}
			<span class="min-w-0 leading-5 wrap-anywhere">
				<HostHoverCard sub={s}>
					<span
						class="font-mono text-sm leading-5 font-medium {s.is_active
							? ''
							: 'text-muted-foreground'}"
					>
						{#each headLabels as part, i (i)}{part}{#if i < headLabels.length - 1}.<wbr
								/>{/if}{/each}{#if apexSuffix}<wbr /><span class="font-normal text-muted-foreground"
								>{apexSuffix}</span
							>{/if}
					</span>
				</HostHoverCard>
			</span>
			{#if worstSeverity}
				<Hint
					text="{s.vuln_count} {s.vuln_count === 1
						? 'finding'
						: 'findings'} on this host, worst is {severityLabel(
						worstSeverity
					).toLowerCase()}{s.vuln_kev ? ' and known exploited' : ''}"
				>
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							class="flex h-5 shrink-0 items-center gap-1 rounded border px-1 text-[10px] hover:bg-accent"
							style="border-color:color-mix(in oklch, {SEVERITY_FILL[
								worstSeverity
							]} 45%, transparent)"
							onclick={(e) => {
								stopProp(e);
								onVulns?.(exactToken('host', s.name));
							}}
						>
							<span class="size-1.5 rounded-full" style="background:{SEVERITY_FILL[worstSeverity]}"
							></span>
							{s.vuln_count}
							{#if s.vuln_kev}<Flame class="size-2.5 text-destructive" />{/if}
						</button>
					{/snippet}
				</Hint>
			{/if}
			{#if s.is_wildcard}
				<span class="flex h-5 shrink-0 items-center">
					<Badge variant="outline" class="px-1 text-[10px] font-normal text-muted-foreground">
						wildcard
					</Badge>
				</span>
			{/if}
			{#if !s.is_active}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<span
								class="flex h-5 shrink-0 items-center text-[10px] text-muted-foreground/70"
								{...props}>no DNS</span
							>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content side="right">Did not resolve to an address</Tooltip.Content>
				</Tooltip.Root>
			{/if}
			<span class="hidden h-5 shrink-0 items-center sm:flex">
				<CopyButton
					value={s.name}
					class="size-6 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
				/>
			</span>
		</div>

		{#if s.http_status}
			<div class="flex items-start gap-1.5 text-xs text-muted-foreground sm:hidden">
				{@render title('line-clamp-1')}
			</div>
		{/if}

		{#if s.cname}
			<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
				<CornerDownRight class="size-3 shrink-0" />
				{#if provider}
					{@const ProvIcon = PROVIDER_KIND_ICONS[provider.kind]}
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<button
									{...props}
									type="button"
									class="inline-flex shrink-0 items-center gap-1 rounded border border-border px-1 text-[11px] hover:bg-accent hover:text-foreground"
									onclick={(e) => pivot(e, filterToken('cname', provider.suffix))}
								>
									<TechIcon name={provider.label} class="size-3">
										{#snippet fallback()}
											<ProvIcon class="size-3" />
										{/snippet}
									</TechIcon>
									{provider.label}
								</button>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content>
							{PROVIDER_KIND_LABELS[provider.kind]} · filter hosts on {provider.label}
						</Tooltip.Content>
					</Tooltip.Root>
				{/if}
				<Hint text="Filter hosts pointing at {s.cname}">
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							class="min-w-0 truncate font-mono text-[11px] hover:text-foreground"
							onclick={(e) => pivot(e, cnameToken)}
						>
							{s.cname}
						</button>
					{/snippet}
				</Hint>
			</div>
		{:else if redirected}
			<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
				<CornerDownRight class="size-3 shrink-0" />
				<Hint text={s.final_url}>
					{#snippet child(props)}
						<span {...props} class="min-w-0 truncate font-mono text-[11px]">{s.final_url}</span>
					{/snippet}
				</Hint>
			</div>
		{/if}

		{#if matches.length}
			<MatchChips {matches} suppress={suppressed} onOpen={(field) => onEvidence(s, field)} />
		{/if}

		{#if signals}
			<div class="flex flex-wrap items-center gap-1.5 pt-0.5">
				{#if cert === 'expired'}
					{@render signal(
						'Cert expired',
						expiry
							? `Expired ${expiry} · filter hosts with an expired cert`
							: 'Filter hosts with an expired cert',
						'cert:expired',
						'border-destructive/30 text-destructive',
						ShieldX
					)}
				{:else if cert === 'expiring'}
					{@render signal(
						`Cert expires in ${daysUntilExpiry(s)}d`,
						`Expires ${expiry} · filter hosts with an expiring cert`,
						'cert:expiring',
						'border-warning/30 text-warning',
						CalendarClock
					)}
				{:else if cert === 'self-signed'}
					{@render signal(
						'Self-signed cert',
						'Filter hosts with a self-signed cert',
						'cert:self-signed',
						'border-warning/30 text-warning',
						ShieldAlert
					)}
				{/if}
				{#if internalIp}
					{@render signal(
						'Internal IP',
						`Resolves to private address ${internalIp} · filter hosts on it`,
						filterToken('ip', internalIp),
						'border-warning/30 text-warning',
						Network
					)}
				{/if}
				{#if s.waf}
					{@render signal(
						`WAF ${s.waf}`,
						'Behind a web application firewall · filter hosts with a WAF',
						'is:waf',
						'border-border text-muted-foreground',
						ShieldCheck
					)}
				{/if}
			</div>
		{/if}
	</div>

	<div class="w-12 shrink-0 sm:w-16">
		<Tooltip.Root>
			<Tooltip.Trigger>
				{#snippet child({ props })}
					<span
						{...props}
						class="inline-flex items-center gap-1 font-mono text-xs {httpStatusTextClass(
							s.http_status
						)}"
					>
						{#if s.http_status == null}
							—
						{:else}
							{#if AUTH_CODES.has(s.http_status)}
								<Lock class="size-3" />
							{:else if statusCls === 'info'}
								<ArrowRight class="size-3" />
							{:else}
								<span class="size-1.5 rounded-full {STATUS_DOT[statusCls]}"></span>
							{/if}
							{s.http_status}
						{/if}
					</span>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content>
				{httpStatusReason(
					s.http_status
				)}{#if s.http_status != null && AUTH_CODES.has(s.http_status)}
					· requires authentication{/if}
			</Tooltip.Content>
		</Tooltip.Root>
	</div>

	<div class="hidden min-w-40 flex-[2] items-start gap-1.5 text-xs text-muted-foreground sm:flex">
		{@render title('line-clamp-2')}
	</div>

	{#each columns as col (col.key)}
		<div class="hidden shrink-0 sm:block {col.width} {col.align === 'right' ? 'text-right' : ''}">
			{#if col.key === 'tech'}
				{#if s.tech.length}
					<div class="flex flex-wrap items-center gap-1">
						{#each s.tech.slice(0, MAX_TECH) as t (t)}
							<Tooltip.Root>
								<Tooltip.Trigger>
									{#snippet child({ props })}
										<button
											{...props}
											type="button"
											class="flex max-w-full min-w-0"
											onclick={(e) => pivot(e, filterToken('tech', t))}
										>
											<Badge
												variant="outline"
												class="max-w-full min-w-0 cursor-pointer font-normal hover:bg-accent"
											>
												<TechIcon name={t} />
												<span class="truncate">{t}</span>
											</Badge>
										</button>
									{/snippet}
								</Tooltip.Trigger>
								<Tooltip.Content class="flex items-center gap-1.5">
									<TechIcon name={t} class="size-3.5" />
									{t}
								</Tooltip.Content>
							</Tooltip.Root>
						{/each}
						<OverflowPopover
							items={s.tech}
							shown={MAX_TECH}
							label="technologies"
							icons
							onSelect={(t) => onFilter(filterToken('tech', t))}
						/>
					</div>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'ip'}
				{#if ips.length}
					<div class="flex flex-col items-start gap-0.5">
						{#each ips.slice(0, MAX_IPS) as ip (ip)}
							<Hint text="Filter hosts on {ip}">
								{#snippet child(props)}
									<button
										{...props}
										type="button"
										class="max-w-full truncate text-left font-mono text-xs hover:underline {isPrivateIp(
											ip
										)
											? 'text-warning'
											: ''}"
										onclick={(e) => pivot(e, filterToken('ip', ip))}
									>
										{ip}
									</button>
								{/snippet}
							</Hint>
						{/each}
						<OverflowPopover
							items={ips}
							shown={MAX_IPS}
							label="IP addresses"
							mono
							onSelect={(ip) => onFilter(filterToken('ip', ip))}
						/>
					</div>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
				{#if s.asn}
					<Hint text={s.asn_org ? `AS${s.asn} · ${s.asn_org}` : `AS${s.asn}`}>
						{#snippet child(props)}
							<div {...props} class="mt-0.5 truncate text-[11px] text-muted-foreground">
								<span class="font-mono">AS{s.asn}</span>{#if s.asn_org}
									· {s.asn_org}{/if}
							</div>
						{/snippet}
					</Hint>
				{/if}
				{#if s.is_cdn}
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<span {...props} class="mt-1 inline-flex">
									<Badge variant="info" class="px-1 text-[10px] font-normal">
										<TechIcon name={s.cdn_name ?? ''} class="size-2.5" />
										{s.cdn_name ?? 'CDN'}
									</Badge>
								</span>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content>Fronted by a CDN</Tooltip.Content>
					</Tooltip.Root>
				{/if}
			{:else if col.key === 'ports'}
				{#if ports.length}
					<div class="flex flex-wrap items-center gap-1">
						{#each ports.slice(0, MAX_PORTS) as p (p)}
							<PortHoverCard
								port={p}
								load={() => loadServices(s.name)}
								onServices={onServices ? (n) => onServices(s.name, n) : undefined}
							>
								<button type="button" onclick={(e) => pivot(e, filterToken('port', String(p)))}>
									<Badge
										variant="outline"
										class="cursor-pointer px-1 font-mono text-[10px] font-normal hover:bg-accent {isSensitivePort(
											p
										)
											? 'border-warning/40 text-warning'
											: ''}"
									>
										{p}
									</Badge>
								</button>
							</PortHoverCard>
						{/each}
						<PortOverflow
							{ports}
							shown={MAX_PORTS}
							load={() => loadServices(s.name)}
							onSelect={(p) => onFilter(filterToken('port', String(p)))}
						/>
					</div>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'sources'}
				<div class="flex flex-wrap items-center gap-1">
					{#each (s.sources ?? []).slice(0, MAX_SOURCES) as src (src)}
						<button type="button" onclick={(e) => pivot(e, filterToken('source', src))}>
							<Badge
								variant="outline"
								class="cursor-pointer px-1 text-[10px] font-normal text-muted-foreground hover:bg-accent"
							>
								{src}
							</Badge>
						</button>
					{/each}
					<OverflowPopover
						items={s.sources ?? []}
						shown={MAX_SOURCES}
						label="sources"
						onSelect={(src) => onFilter(filterToken('source', src))}
					/>
				</div>
			{:else if col.key === 'discovered'}
				<Hint text={s.discovered_at}>
					{#snippet child(props)}
						<div {...props} class="text-xs text-muted-foreground">
							{relativeTime(s.discovered_at)}
						</div>
					{/snippet}
				</Hint>
				{#if s.discovered_at}
					<div class="text-[11px] text-muted-foreground/70">{formatShortDate(s.discovered_at)}</div>
				{/if}
			{:else if col.key === 'screenshot'}
				{#if s.screenshot_path}
					<ScreenshotThumb path={s.screenshot_path} alt={s.name} class="h-14 w-24" preview />
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'size'}
				<span class="font-mono text-xs text-muted-foreground tabular-nums">
					{formatBytes(s.content_length)}
				</span>
			{:else if col.key === 'time'}
				<span class="font-mono text-xs text-muted-foreground tabular-nums">
					{formatResponseTime(s.response_time)}
				</span>
			{/if}
		</div>
	{/each}

	<div class={ACTIONS_PIN}>
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="{ACTIONS_BODY} {pin}" onclick={stopProp}>
			{#if s.http_url}
				<Button
					variant="ghost"
					size="icon"
					class="hidden size-7 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 sm:inline-flex"
					href={s.http_url}
					target="_blank"
					rel="noreferrer noopener"
					aria-label="Open {s.name} in browser"
				>
					<ExternalLink class="h-4 w-4" />
				</Button>
			{/if}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7"
							aria-label="Actions for {s.name}"
						>
							<Ellipsis class="h-4 w-4" />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-48">
					<DropdownMenu.Group>
						{#if s.http_url}
							<DropdownMenu.Item class="gap-2">
								{#snippet child({ props })}
									<a {...props} href={s.http_url} target="_blank" rel="noreferrer noopener">
										<ExternalLink class="h-4 w-4" /> Open in browser
									</a>
								{/snippet}
							</DropdownMenu.Item>
						{/if}
						<DropdownMenu.Item onclick={() => copy(s.name)} class="gap-2">
							<Copy class="h-4 w-4" /> Copy host
						</DropdownMenu.Item>
						{#if s.http_url}
							<DropdownMenu.Item onclick={() => copy(s.http_url ?? '')} class="gap-2">
								<Link class="h-4 w-4" /> Copy URL
							</DropdownMenu.Item>
						{/if}
					</DropdownMenu.Group>
					{#if ips[0] || s.cname || s.favicon_hash}
						<DropdownMenu.Separator />
						<DropdownMenu.Group>
							<DropdownMenu.Label>Pivot</DropdownMenu.Label>
							{#if ips[0]}
								<DropdownMenu.Item
									onclick={() => onFilter(filterToken('ip', ips[0]))}
									class="gap-2"
								>
									<Filter class="h-4 w-4" /> Same IP
								</DropdownMenu.Item>
							{/if}
							{#if s.cname}
								<DropdownMenu.Item onclick={() => onFilter(cnameToken)} class="gap-2">
									<Filter class="h-4 w-4" /> Same CNAME
								</DropdownMenu.Item>
							{/if}
							{#if s.favicon_hash}
								<DropdownMenu.Item onclick={() => onFilter(faviconToken)} class="gap-2">
									<Filter class="h-4 w-4" /> Same favicon
								</DropdownMenu.Item>
							{/if}
						</DropdownMenu.Group>
					{/if}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
</div>
