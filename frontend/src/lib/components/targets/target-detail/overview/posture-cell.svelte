<script lang="ts">
	import Plug from '@lucide/svelte/icons/plug';
	import Cell from '$lib/components/cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { Spinner } from '$lib/components/ui/spinner';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { IconComponent } from '$lib/config/icons';
	import type { Check, CheckStatus } from './derive';

	interface Props {
		targetId: string;
		checks: Check[];
		sensitive: number;
		servicesScanId: string | null;
		loading?: boolean;
		class?: string;
	}

	let {
		targetId,
		checks,
		sensitive,
		servicesScanId,
		loading = false,
		class: className = ''
	}: Props = $props();

	const SERVICES = SURFACE[SurfaceDimension.SERVICES];
	const RANK: Record<CheckStatus, number> = { fail: 0, warn: 1, pending: 2, info: 3, pass: 4 };
	const DOT: Record<CheckStatus, string> = {
		fail: 'bg-destructive',
		warn: 'bg-warning',
		pending: 'bg-info',
		info: 'bg-muted-foreground/60',
		pass: 'bg-success'
	};

	interface Row {
		key: string;
		status: CheckStatus;
		label: string;
		detail?: string;
		count?: string;
		icon: IconComponent;
		href?: string;
	}

	let rows = $derived.by<Row[]>(() => {
		const out: Row[] = checks.map((c) => ({
			key: c.key,
			status: c.status,
			label: c.label,
			detail: c.detail,
			count: c.count ? `${c.count}${c.unit ? ` ${c.unit}` : ''}` : undefined,
			icon: c.icon,
			href: c.tab ? ROUTES.target(targetId, c.tab) : undefined
		}));
		if (sensitive > 0 && servicesScanId)
			out.push({
				key: 'sensitive',
				status: 'warn',
				label: sensitive === 1 ? 'Sensitive service' : 'Sensitive services',
				detail: 'Databases, remote access and admin ports open',
				count: sensitive.toLocaleString(),
				icon: Plug,
				href: ROUTES.scanTab(servicesScanId, SERVICES.tab, {
					[SERVICES.queryParam]: 'is:sensitive'
				})
			});
		return out.sort((a, b) => RANK[a.status] - RANK[b.status]);
	});
	let review = $derived(rows.filter((r) => r.status === 'fail' || r.status === 'warn').length);
	let pass = $derived(rows.filter((r) => r.status === 'pass').length);
</script>

<Cell
	skeleton="list"
	id="posture"
	title="Posture"
	loading={loading && !rows.length}
	class={className}
>
	{#if rows.length}
		<ul class="flex flex-col">
			{#each rows as r (r.key)}
				{@const Icon = r.icon}
				<li class="border-t first:border-t-0">
					<svelte:element
						this={r.href ? 'a' : 'div'}
						href={r.href}
						class="-mx-2 grid grid-cols-[auto_auto_minmax(0,1fr)_auto] items-start gap-x-2.5 rounded-md px-2 py-1.5 text-sm {r.href
							? 'transition-colors hover:bg-muted/40'
							: ''}"
					>
						<span class="flex h-5 items-center">
							<span class="size-2 rounded-full {DOT[r.status]}" aria-hidden="true"></span>
						</span>
						<span class="flex h-5 items-center text-muted-foreground">
							{#if r.status === 'pending'}<Spinner class="size-3.5" />{:else}<Icon
									class="size-3.5"
								/>{/if}
						</span>
						<span class="flex min-w-0 flex-col">
							<span class="leading-5 {r.status === 'pass' ? 'text-muted-foreground' : ''}"
								>{r.label}</span
							>
							{#if r.detail}
								<Hint text={r.detail}>
									{#snippet child(props)}
										<span {...props} class="truncate text-2xs text-muted-foreground"
											>{r.detail}</span
										>
									{/snippet}
								</Hint>
							{/if}
						</span>
						{#if r.count}
							<span class="flex h-5 items-center text-xs font-medium tabular-nums">{r.count}</span>
						{/if}
					</svelte:element>
				</li>
			{/each}
		</ul>
	{:else}
		<span class="text-sm text-muted-foreground">No check</span>
	{/if}
	{#snippet footer()}
		<span>{review} to review · {pass} pass</span>
	{/snippet}
</Cell>
