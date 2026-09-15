<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { SvelteSet } from 'svelte/reactivity';
	import SignalSheet, { type SheetRow } from '$lib/components/dashboard/signal-sheet.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { ESTATE_STRENGTH_LABELS, EstateStrength, PROVIDER_KIND_LABELS } from '$lib/config/estate';
	import type { EstateDomain, EstateNeighbourCert, EstateProvider } from '$lib/types/estate';

	interface Props {
		open: boolean;
		onOpenChange: (open: boolean) => void;
		title: string;
		description?: string;
		domains: EstateDomain[];
		providers?: EstateProvider[];
		neighbours?: EstateNeighbourCert[];
		loading?: boolean;
		onAdded?: (domain: string) => void;
	}

	let {
		open,
		onOpenChange,
		title,
		description,
		domains,
		providers = [],
		neighbours = [],
		loading = false,
		onAdded
	}: Props = $props();

	let added = new SvelteSet<string>();
	let pending = $state<string | null>(null);
	let adding = $state(false);

	export function evidence(d: EstateDomain): string {
		return d.signals.map((s) => (s.detail ? `${s.label} ${s.detail}` : s.label)).join(' · ');
	}

	async function addTarget(domain: string): Promise<boolean> {
		const slug = projectsStore.activeProject?.slug;
		if (!slug) return false;
		try {
			await targetsApi.create({ target_value: domain, project_slug: slug });
			added.add(domain);
			onAdded?.(domain);
			return true;
		} catch {
			return false;
		}
	}

	async function addOne(domain: string) {
		pending = domain;
		const ok = await addTarget(domain);
		pending = null;
		if (ok) toast.success(`Target ${domain} added`);
		else toast.error(`Target ${domain} not added`);
	}

	let candidates = $derived(domains.filter((d) => !d.target_id && !added.has(d.domain)));

	async function addAll() {
		adding = true;
		let n = 0;
		for (const d of candidates) if (await addTarget(d.domain)) n += 1;
		adding = false;
		if (n) toast.success(`${n} ${n === 1 ? 'target' : 'targets'} added`);
		else toast.error('Targets not added');
	}

	let rows = $derived.by<SheetRow[]>(() => {
		const out: SheetRow[] = [];
		for (const d of domains) {
			const tracked = !!d.target_id;
			const sources = d.sources.length
				? ` · from ${d.sources.map((s) => s.target_value).join(', ')}`
				: '';
			out.push({
				key: d.domain,
				primary: d.domain,
				secondary: `${evidence(d)}${sources}`,
				meta: ESTATE_STRENGTH_LABELS[d.strength ? EstateStrength.DIRECT : EstateStrength.SHARED],
				group: tracked ? 'Targets' : 'Not a target',
				href: tracked ? ROUTES.target(d.target_id!) : undefined,
				action: tracked
					? undefined
					: {
							label: 'Add',
							doneLabel: 'Added',
							done: added.has(d.domain),
							pending: pending === d.domain,
							onClick: () => addOne(d.domain)
						}
			});
		}
		for (const p of providers)
			out.push({
				key: `provider:${p.name}:${p.kind}`,
				primary: p.name,
				secondary: p.detail,
				meta: `${PROVIDER_KIND_LABELS[p.kind] ?? p.kind} · ${p.count}`,
				group: 'Runs on'
			});
		for (const n of neighbours)
			out.push({
				key: `neighbour:${n.host}:${n.subject}`,
				primary: n.host,
				secondary: `${n.subject}${n.provider ? ` · ${n.provider}` : ''}`,
				meta: `${n.names} names`,
				group: 'Platform neighbours'
			});
		return out;
	});
</script>

<SignalSheet
	{open}
	{onOpenChange}
	{title}
	{description}
	{rows}
	noun="Domains"
	{loading}
	action={candidates.length > 1 && !adding
		? { label: `Add ${candidates.length} targets`, onClick: addAll }
		: null}
/>
