<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import PanelHead from './panel-head.svelte';
	import CompositionBar from './composition-bar.svelte';
	import type { Segment } from './composition-bar.svelte';
	import { CHART_FILL } from './palette';
	import type { InsightBucket, SubdomainInsights } from '$lib/utilities/scan-insights';

	interface Props {
		insights: SubdomainInsights | null;
		loading: boolean;
		isDomain: boolean;
		nounPlural: string;
		onFilter: (search: string) => void;
	}

	let { insights, loading, isDomain, nounPlural, onFilter }: Props = $props();

	const STATUS_FILTER: Record<string, string> = {
		live: 'status:2xx',
		redirect: 'status:3xx',
		auth: 'status:401 or status:403',
		error: '(status:4xx or status:5xx) and not status:401 and not status:403'
	};
	const NO_HTTP_KEY = 'none';
	const NO_HTTP_FILTER = 'status:none';
	const CERT_FILTER: Record<string, string> = {
		expired: 'cert:expired',
		d7: 'cert.expires:<7d and not cert:expired',
		d30: 'cert.expires:<30d and not cert.expires:<7d',
		d90: 'cert.expires:<90d and not cert.expires:<30d',
		ok: 'cert.expires:>=90d'
	};
	const EXPIRING_KEYS = new Set(['expired', 'd7', 'd30']);
	const EXPIRING_FILTER = 'cert.expires:<30d';
	const CNAME_KEY = 'cname';
	const DNS_FILTER: Record<string, string> = {
		resolved: 'is:resolved',
		cname: 'cname:. and not is:resolved',
		unresolved: 'not is:resolved and not cname:.'
	};

	interface Cell {
		key: string;
		title: string;
		subtitle: string;
		segments: Segment[];
		total: number;
		note?: { text: string; filter?: string };
	}

	const toSegments = (buckets: InsightBucket[], filters: Record<string, string>): Segment[] =>
		buckets
			.filter((b) => b.count > 0)
			.map((b) => ({
				key: b.key,
				label: b.label,
				count: b.count,
				color: CHART_FILL[b.klass],
				filter: filters[b.key]
			}));
	const sum = (xs: { count: number }[]) => xs.reduce((n, d) => n + d.count, 0);

	let cells = $derived.by<Cell[]>(() => {
		if (!insights) return [];
		const out: Cell[] = [];

		const http = toSegments(
			insights.status_reframe.filter((b) => b.key !== NO_HTTP_KEY),
			STATUS_FILTER
		);
		const noHttp = insights.status_reframe.find((b) => b.key === NO_HTTP_KEY)?.count ?? 0;
		if (http.length) {
			const total = sum(http);
			out.push({
				key: 'http',
				title: 'HTTP responses',
				subtitle: `${total.toLocaleString()} web hosts`,
				segments: http,
				total,
				note:
					noHttp > 0
						? {
								text: `${noHttp.toLocaleString()} ${nounPlural} with no HTTP response`,
								filter: NO_HTTP_FILTER
							}
						: undefined
			});
		}

		const certs = toSegments(insights.cert_buckets, CERT_FILTER);
		if (certs.length) {
			const total = sum(certs);
			const expiring = sum(certs.filter((s) => EXPIRING_KEYS.has(s.key)));
			out.push({
				key: 'certs',
				title: 'Certificates',
				subtitle: `${total.toLocaleString()} TLS ${total === 1 ? 'certificate' : 'certificates'}`,
				segments: certs,
				total,
				note:
					expiring > 0
						? {
								text: `${expiring.toLocaleString()} ${expiring === 1 ? 'certificate expires' : 'certificates expire'} within 30 days`,
								filter: EXPIRING_FILTER
							}
						: { text: 'No certificate expires within 30 days' }
			});
		}

		if (isDomain) {
			const dns = toSegments(insights.resolution, DNS_FILTER);
			const cnameOnly = dns.find((s) => s.key === CNAME_KEY)?.count ?? 0;
			if (dns.length)
				out.push({
					key: 'dns',
					title: 'DNS resolution',
					subtitle: `${sum(dns).toLocaleString()} ${nounPlural}`,
					segments: dns,
					total: sum(dns),
					note:
						cnameOnly > 0
							? {
									text: `${cnameOnly.toLocaleString()} CNAME-only ${cnameOnly === 1 ? 'record is a' : 'records are'} takeover ${cnameOnly === 1 ? 'candidate' : 'candidates'}`,
									filter: DNS_FILTER[CNAME_KEY]
								}
							: { text: 'No CNAME-only records' }
				});
		}
		return out;
	});
</script>

{#if (loading && !insights) || cells.length}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Posture" />
		<div
			class="-mt-px -ml-px grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(14.5rem,1fr))]"
		>
			{#if !insights}
				{#each Array(3) as _, i (i)}
					<div class="flex flex-col gap-4 border-t border-l p-5">
						<Skeleton class="h-4 w-32" />
						<Skeleton class="h-1.5 w-full" />
						<Skeleton class="h-16 w-full" />
					</div>
				{/each}
			{:else}
				{#each cells as c (c.key)}
					<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
						<div class="flex flex-col gap-0.5">
							<h3 class="text-sm font-medium">{c.title}</h3>
							<p class="text-xs text-muted-foreground">{c.subtitle}</p>
						</div>
						<CompositionBar
							segments={c.segments}
							total={c.total}
							label={c.title}
							onSelect={onFilter}
						/>
						{#if c.note}
							{@const note = c.note}
							<div class="mt-auto flex flex-col items-start pt-1 text-xs text-muted-foreground">
								{#if note.filter}
									<Button
										variant="link"
										size="sm"
										class="h-auto gap-1 px-0 text-xs"
										onclick={() => onFilter(note.filter!)}
									>
										{note.text}
										<ChevronRight class="size-3.5" />
									</Button>
								{:else}
									<span>{note.text}</span>
								{/if}
							</div>
						{/if}
					</section>
				{/each}
			{/if}
		</div>
	</Card.Root>
{/if}
