<script lang="ts">
	import type { WhoisSummaryData } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import { goto } from '$app/navigation';
	import {
		formatShortDate,
		formatMonthYear,
		getExpirationUrgency,
		formatExpirationLabel,
		getDomainAge,
		type ExpirationUrgency
	} from '$lib/utilities/dates';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import {
		Globe,
		Server,
		Network,
		Clock,
		CalendarDays,
		CalendarClock,
		Building,
		UserRound,
		TriangleAlert,
		Loader,
		Flag,
		ExternalLink
	} from 'lucide-svelte';

	interface Props {
		status: TaskStatus;
		whois: WhoisSummaryData | null;
		targetId: string;
		error?: string | null;
		onClick?: () => void;
	}

	let { status, whois, targetId, error = null, onClick }: Props = $props();

	let urgency = $derived<ExpirationUrgency>(
		whois?.expiration_date ? getExpirationUrgency(whois.expiration_date) : 'none'
	);

	let expirationLabel = $derived(
		whois?.expiration_date ? formatExpirationLabel(whois.expiration_date) : ''
	);

	let domainAge = $derived(whois?.registration_date ? getDomainAge(whois.registration_date) : '');

	let inlineSummary = $derived.by(() => {
		if (!whois) return '';

		switch (whois.lookup_type) {
			case 'DOMAIN': {
				const registrar = whois.registrar_name ? truncate(whois.registrar_name, 24) : '';
				const expiry = whois.expiration_date ? formatMonthYear(whois.expiration_date) : '';
				return [registrar, expiry ? `Exp ${expiry}` : ''].filter(Boolean).join(' · ');
			}
			case 'IP': {
				const name = whois.name ? truncate(whois.name, 20) : '';
				const cidr = whois.network_cidr || '';
				const country = whois.country || '';
				return [name, cidr, country].filter(Boolean).join(' · ');
			}
			case 'ASN': {
				const name = whois.name ? truncate(whois.name, 20) : '';
				const registrant = whois.registrant_name ? truncate(whois.registrant_name, 24) : '';
				return [name, registrant].filter(Boolean).join(' · ');
			}
			default:
				return '';
		}
	});

	let urgencyClasses = $derived.by(() => {
		const map: Record<ExpirationUrgency, string> = {
			expired: 'text-red-500 dark:text-red-400',
			critical: 'text-red-500 dark:text-red-400',
			warning: 'text-amber-500 dark:text-amber-400',
			healthy: 'text-emerald-600 dark:text-emerald-400',
			none: 'text-muted-foreground'
		};
		return map[urgency];
	});

	let urgencyDotClasses = $derived.by(() => {
		const map: Record<ExpirationUrgency, string> = {
			expired: 'bg-red-500',
			critical: 'bg-red-500',
			warning: 'bg-amber-500',
			healthy: 'bg-emerald-500',
			none: 'bg-muted-foreground'
		};
		return map[urgency];
	});

	let LookupIcon = $derived.by(() => {
		if (!whois) return Globe;
		switch (whois.lookup_type) {
			case 'DOMAIN':
				return Globe;
			case 'IP':
				return Server;
			case 'ASN':
				return Network;
			default:
				return Globe;
		}
	});

	function truncate(str: string, max: number): string {
		if (str.length <= max) return str;
		return str.slice(0, max - 1) + '…';
	}

	function handleClick(e: MouseEvent) {
		e.stopPropagation();
		onClick?.();
	}
</script>

{#if status === TaskStatus.PENDING || status === TaskStatus.QUERYING}
	<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
		<Loader class="h-3 w-3 animate-spin" />
		<span class="animate-pulse">Fetching WHOIS…</span>
	</div>
{:else if status === TaskStatus.FAILED}
	<div class="flex items-center gap-1.5 text-xs text-red-500/70 dark:text-red-400/70">
		<TriangleAlert class="h-3 w-3" />
		<span>WHOIS failed</span>
	</div>
{:else if status === TaskStatus.SUCCESS && whois}
	<HoverCard.Root openDelay={250} closeDelay={100}>
		<HoverCard.Trigger>
			<button
				type="button"
				class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer max-w-full"
				onclick={handleClick}
			>
				<span class="truncate">{inlineSummary}</span>
				{#if urgency !== 'none' && whois.lookup_type === 'DOMAIN'}
					<span class="inline-block h-1.5 w-1.5 rounded-full shrink-0 {urgencyDotClasses}"></span>
				{/if}
			</button>
		</HoverCard.Trigger>
		<HoverCard.Content class="w-80 p-0" align="start" side="bottom">
			<!-- Header -->
			<div class="px-4 pt-3.5 pb-3 border-b border-border/50">
				<div class="flex items-center gap-2">
					<div class="flex items-center justify-center h-8 w-8 rounded-lg bg-primary/10">
						<LookupIcon class="h-4 w-4 text-primary" />
					</div>
					<div class="min-w-0 flex-1">
						<p class="text-sm font-medium truncate">{whois.name || whois.query_value}</p>
						<p class="text-xs text-muted-foreground">{whois.lookup_type} Record</p>
					</div>
				</div>
			</div>

			<!-- Body -->
			<div class="px-4 py-3 space-y-3">
				{#if whois.registrant_name}
					<div class="flex items-start gap-2.5">
						<UserRound class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
						<div class="min-w-0">
							<p
								class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1"
							>
								Registrant
							</p>
							<p class="text-sm truncate">{whois.registrant_name}</p>
						</div>
					</div>
				{/if}

				{#if whois.registrar_name}
					<div class="flex items-start gap-2.5">
						<Building class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
						<div class="min-w-0">
							<p
								class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1"
							>
								Registrar
							</p>
							<p class="text-sm truncate">{whois.registrar_name}</p>
						</div>
					</div>
				{/if}

				{#if whois.network_cidr}
					<div class="flex items-start gap-2.5">
						<Network class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
						<div class="min-w-0">
							<p
								class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1"
							>
								Network
							</p>
							<p class="text-sm font-mono">{whois.network_cidr}</p>
						</div>
					</div>
				{/if}

				{#if whois.country}
					<div class="flex items-start gap-2.5">
						<Flag class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
						<div class="min-w-0">
							<p
								class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1"
							>
								Country
							</p>
							<p class="text-sm">{whois.country}</p>
						</div>
					</div>
				{/if}

				{#if whois.registration_date || whois.expiration_date}
					<div class="pt-1 border-t border-border/40">
						<div class="grid grid-cols-2 gap-3 pt-2">
							{#if whois.registration_date}
								<div class="flex items-start gap-2">
									<CalendarDays class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
									<div>
										<p
											class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1"
										>
											Registered
										</p>
										<p class="text-xs font-medium">{formatShortDate(whois.registration_date)}</p>
										{#if domainAge}
											<p class="text-[11px] text-muted-foreground mt-0.5">{domainAge}</p>
										{/if}
									</div>
								</div>
							{/if}

							{#if whois.expiration_date}
								<div class="flex items-start gap-2">
									<CalendarClock class="h-3.5 w-3.5 mt-0.5 shrink-0 {urgencyClasses}" />
									<div>
										<p
											class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1"
										>
											Expires
										</p>
										<p class="text-xs font-medium">{formatShortDate(whois.expiration_date)}</p>
										{#if expirationLabel}
											<p class="text-[11px] mt-0.5 font-medium {urgencyClasses}">
												{expirationLabel}
											</p>
										{/if}
									</div>
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="px-4 py-2.5 border-t border-border/50 bg-muted/30">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
						<Clock class="h-3 w-3" />
						<span>Queried {formatShortDate(whois.queried_at)}</span>
					</div>
					<button
						type="button"
						class="flex items-center gap-1 text-[11px] text-primary/70 hover:text-primary transition-colors"
						onclick={() => goto(`/targets/${targetId}`)}
					>
						See Details
						<ExternalLink class="h-2.5 w-2.5" />
					</button>
				</div>
			</div>
		</HoverCard.Content>
	</HoverCard.Root>
{/if}
