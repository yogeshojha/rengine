<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import SignalSheet, { type SheetRow } from '$lib/components/dashboard/signal-sheet.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		ESTATE_STRENGTH_LABELS,
		EstateStrength,
		EstateTriageState,
		PROVIDER_KIND_LABELS
	} from '$lib/config/estate';
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
		onTriaged?: (domain: string, state: string) => void;
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
		onAdded,
		onTriaged
	}: Props = $props();

	let added = new SvelteSet<string>();
	let pending = $state<string | null>(null);
	let adding = $state(false);
	let states = new SvelteMap<string, string>();
	let triaging = $state<string | null>(null);

	const stateOf = (d: EstateDomain) => states.get(d.domain) ?? d.state;

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

	async function setState(domain: string, next: EstateTriageState) {
		const projectId = projectsStore.activeProject?.id;
		if (!projectId) return;
		const previous = states.get(domain);
		states.set(domain, next);
		triaging = domain;
		try {
			await targetsApi.estateTriage(projectId, [domain], next);
			onTriaged?.(domain, next);
			toast.success(
				next === EstateTriageState.DISMISSED ? `${domain} dismissed` : `${domain} restored`
			);
		} catch {
			if (previous === undefined) states.delete(domain);
			else states.set(domain, previous);
			toast.error(
				next === EstateTriageState.DISMISSED ? `${domain} not dismissed` : `${domain} not restored`
			);
		} finally {
			triaging = null;
		}
	}

	let candidates = $derived(
		domains.filter(
			(d) => !d.target_id && !added.has(d.domain) && stateOf(d) === EstateTriageState.OPEN
		)
	);

	async function addAll() {
		adding = true;
		let n = 0;
		for (const d of candidates) if (await addTarget(d.domain)) n += 1;
		adding = false;
		if (n) toast.success(`${n} ${n === 1 ? 'target' : 'targets'} added`);
		else toast.error('Targets not added');
	}

	function rowBadge(d: EstateDomain) {
		if (d.dossier?.takeover_provider)
			return {
				label: `Takeover · ${d.dossier.takeover_provider}`,
				variant: 'warning' as const
			};
		const p = d.program;
		if (!p || !p.in_scope) return undefined;
		return p.eligible_for_bounty
			? { label: `Bounty · ${p.name}`, variant: 'success' as const }
			: { label: `In scope · ${p.name}`, variant: 'secondary' as const };
	}

	function dossierNote(d: EstateDomain): string | undefined {
		const x = d.dossier;
		if (!x || !x.checked_at) return undefined;
		const parts: string[] = [];
		if (x.resolves === true) parts.push(x.ports.length ? `${x.ports.length} ports` : 'Resolves');
		else if (x.resolves === false) parts.push('No address');
		if (x.registered_at) {
			const age = (Date.now() - new Date(x.registered_at).getTime()) / 86400000;
			parts.push(
				age <= 90
					? `registered ${relativeTime(x.registered_at)}`
					: `registered ${new Date(x.registered_at).getFullYear()}`
			);
		}
		return parts.length ? parts.join(' · ') : undefined;
	}

	function domainRow(d: EstateDomain): SheetRow {
		const tracked = !!d.target_id;
		const dismissed = !tracked && stateOf(d) === EstateTriageState.DISMISSED;
		const sources = d.sources.length
			? ` · from ${d.sources.map((s) => s.target_value).join(', ')}`
			: '';
		return {
			key: d.domain,
			primary: d.domain,
			badge: tracked ? undefined : rowBadge(d),
			secondary: `${evidence(d)}${sources}`,
			note: tracked ? undefined : dossierNote(d),
			meta: ESTATE_STRENGTH_LABELS[d.strength ? EstateStrength.DIRECT : EstateStrength.SHARED],
			group: tracked ? 'Targets' : dismissed ? 'Dismissed' : 'Candidates',
			href: tracked ? ROUTES.target(d.target_id!) : undefined,
			action: tracked
				? undefined
				: dismissed
					? {
							label: 'Restore',
							doneLabel: 'Restored',
							pending: triaging === d.domain,
							onClick: () => setState(d.domain, EstateTriageState.OPEN)
						}
					: {
							label: 'Add',
							doneLabel: 'Added',
							done: added.has(d.domain),
							pending: pending === d.domain,
							onClick: () => addOne(d.domain)
						},
			quietAction:
				tracked || dismissed
					? undefined
					: {
							label: 'Dismiss',
							doneLabel: 'Dismissed',
							pending: triaging === d.domain,
							onClick: () => setState(d.domain, EstateTriageState.DISMISSED)
						}
		};
	}

	let rows = $derived.by<SheetRow[]>(() => {
		const open = domains.filter((d) => !d.target_id && stateOf(d) === EstateTriageState.OPEN);
		const tracked = domains.filter((d) => d.target_id);
		const dismissed = domains.filter(
			(d) => !d.target_id && stateOf(d) === EstateTriageState.DISMISSED
		);
		const out: SheetRow[] = [...open, ...tracked].map(domainRow);
		for (const p of providers)
			out.push({
				key: `provider:${p.name}:${p.kind}`,
				primary: p.name,
				secondary: p.detail,
				meta: `${PROVIDER_KIND_LABELS[p.kind] ?? p.kind} · ${p.count}`,
				group: 'Providers'
			});
		for (const n of neighbours)
			out.push({
				key: `neighbour:${n.host}:${n.subject}`,
				primary: n.host,
				secondary: `${n.subject}${n.provider ? ` · ${n.provider}` : ''}`,
				meta: `${n.names} names`,
				group: 'Platform neighbours'
			});
		out.push(...dismissed.map(domainRow));
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
