<script lang="ts" module>
	export const coverage = (h: HostingComposition) =>
		`${h.resolving.toLocaleString()} of ${h.hosts.toLocaleString()} resolve`;

	export const networkNote = (h: HostingComposition) =>
		h.attributed
			? `${h.networks.toLocaleString()} ${h.networks === 1 ? 'network' : 'networks'}`
			: 'Network not attributed';
</script>

<script lang="ts">
	import CompositionBar from './composition-bar.svelte';
	import RankedList, { type RankedRow } from './ranked-list.svelte';
	import { frontingFill } from '$lib/config/hosting';
	import type { HostingComposition, HostingNetwork } from '$lib/types/hosting';

	interface Props {
		hosting: HostingComposition;
		onPick: (query: string) => void;
		class?: string;
	}

	let { hosting, onPick, class: className = '' }: Props = $props();

	const SPLIT_AT = 4;

	const split = (n: HostingNetwork) =>
		n.fronting.map((f) => `${f.label} ${f.count.toLocaleString()}`).join(' · ');

	let fronting = $derived(
		hosting.fronting.map((f) => ({
			key: f.kind,
			label: f.label,
			count: f.count,
			color: frontingFill(f.kind),
			filter: f.query ?? undefined
		}))
	);
	let networks = $derived<RankedRow[]>(
		hosting.by_network.map((n) => {
			const mix = split(n);
			return {
				key: n.id,
				label: n.label,
				meta: n.detail ?? undefined,
				hint: mix ? `${n.label} · ${mix}` : n.label,
				count: n.count,
				filter: n.query ?? undefined,
				segments: n.fronting.map((f) => ({
					key: f.kind,
					count: f.count,
					color: frontingFill(f.kind)
				}))
			};
		})
	);
	let columns = $derived(networks.length > SPLIT_AT ? Math.ceil(networks.length / 2) : 0);
</script>

<div class="flex flex-col gap-4 {className}">
	<CompositionBar
		segments={fronting}
		total={hosting.resolving}
		label="Fronting"
		onSelect={onPick}
		inline
	/>
	{#if networks.length}
		<div class="flex flex-col gap-1.5 border-t pt-3">
			<h3 class="text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">
				Network
			</h3>
			<div class="grid grid-cols-1 gap-x-8 {columns ? 'lg:grid-cols-2' : ''}">
				<RankedList
					rows={columns ? networks.slice(0, columns) : networks}
					base={hosting.resolving}
					onSelect={onPick}
				/>
				{#if columns}
					<RankedList rows={networks.slice(columns)} base={hosting.resolving} onSelect={onPick} />
				{/if}
			</div>
		</div>
	{/if}
</div>
