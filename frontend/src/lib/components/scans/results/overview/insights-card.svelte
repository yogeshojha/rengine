<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Lock from '@lucide/svelte/icons/lock';
	import ShieldOff from '@lucide/svelte/icons/shield-off';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import Plug from '@lucide/svelte/icons/plug';
	import Server from '@lucide/svelte/icons/server';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Link2 from '@lucide/svelte/icons/link-2';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card';
	import * as Item from '$lib/components/ui/item';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { isPrivateIp } from '$lib/utilities/scan-correlation';
	import { targetAssetNoun } from '$lib/types/target';
	import type { IconComponent } from '$lib/config/icons';
	import type { ScanRead } from '$lib/types/scan';
	import type { InsightAttention, InsightCluster } from '$lib/utilities/scan-insights';

	interface Props {
		scan: ScanRead;
		attention: InsightAttention[];
		clusters: InsightCluster[];
		assessed: boolean;
		live: boolean;
		loading: boolean;
		errored: boolean;
		onFilter: (search: string) => void;
		onRescan: () => void;
		onRetry: () => void;
	}

	let {
		scan,
		attention,
		clusters,
		assessed,
		live,
		loading,
		errored,
		onFilter,
		onRescan,
		onRetry
	}: Props = $props();

	type Tone = 'destructive' | 'warning' | 'success' | 'neutral';
	interface Insight {
		key: string;
		tone: Tone;
		icon: IconComponent;
		text: string;
		filter: string;
	}

	const PREVIEW = 6;
	const SHARED_MAX = 2;
	const TONE_ORDER: Record<Tone, number> = { destructive: 0, warning: 1, success: 2, neutral: 3 };
	const TONE_CLASS: Record<Tone, string> = {
		destructive: 'text-destructive',
		warning: 'text-warning',
		success: 'text-success',
		neutral: 'text-muted-foreground'
	};
	const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);
	const ATTENTION: Record<string, { icon: IconComponent; text: (n: number) => string }> = {
		expired: {
			icon: Lock,
			text: (n) => `${n} expired ${plural(n, 'certificate', 'certificates')}`
		},
		expiring: {
			icon: Lock,
			text: (n) => `${n} ${plural(n, 'certificate expires', 'certificates expire')} within 30 days`
		},
		selfsigned: {
			icon: Lock,
			text: (n) => `${n} self-signed ${plural(n, 'certificate', 'certificates')}`
		},
		nowaf: {
			icon: ShieldOff,
			text: (n) => `${n} live ${plural(n, 'host has', 'hosts have')} no WAF`
		},
		server: {
			icon: CircleX,
			text: (n) => `${n} ${plural(n, 'host returns', 'hosts return')} server errors`
		},
		auth: { icon: KeyRound, text: (n) => `${n} login or admin ${plural(n, 'panel', 'panels')}` },
		sensitive: {
			icon: Plug,
			text: (n) => `${n} ${plural(n, 'host exposes', 'hosts expose')} sensitive services`
		}
	};

	let items = $derived.by<Insight[]>(() => {
		const out: Insight[] = [];
		for (const a of attention) {
			const def = ATTENTION[a.key];
			out.push({
				key: a.key,
				tone: a.tone,
				icon: def?.icon ?? TriangleAlert,
				text: def ? def.text(a.count) : `${a.count} ${a.label}`,
				filter: a.filter
			});
		}
		for (const c of clusters) {
			if (c.kind === 'ip' && isPrivateIp(c.value))
				out.push({
					key: `private:${c.value}`,
					tone: 'warning',
					icon: Server,
					text: `${c.count} hosts resolve to private address ${c.value}`,
					filter: `ip:${c.value}`
				});
		}
		const added = scan.new_subdomains ?? 0;
		if (scan.status === 'completed' && scan.is_first_scan === false && added > 0)
			out.push({
				key: 'new',
				tone: 'success',
				icon: Sparkles,
				text: `${added} new ${targetAssetNoun(scan.execution_config.target_type, added)} since the last run`,
				filter: 'is:new'
			});
		let shared = 0;
		for (const c of clusters) {
			if (shared >= SHARED_MAX) break;
			if (c.kind === 'ip' && !isPrivateIp(c.value)) {
				out.push({
					key: `shared:${c.value}`,
					tone: 'neutral',
					icon: Link2,
					text: `${c.count} hosts share ${c.value}`,
					filter: `ip:${c.value}`
				});
				shared++;
			} else if (c.kind === 'cname') {
				out.push({
					key: `cname:${c.value}`,
					tone: 'neutral',
					icon: Link2,
					text: `${c.count} hosts point at ${c.value}`,
					filter: `cname:${c.value}`
				});
				shared++;
			}
		}
		return out.sort((a, b) => TONE_ORDER[a.tone] - TONE_ORDER[b.tone]);
	});

	let expanded = $state(false);
	let visible = $derived(expanded ? items : items.slice(0, PREVIEW));
	let hidden = $derived(items.length - visible.length);
</script>

<Card.Root>
	<Card.Header>
		<Card.Title>Key findings</Card.Title>
		<Card.Description>Exposure signals and shared infrastructure from this scan.</Card.Description>
	</Card.Header>
	<Card.Content class="px-3">
		{#if loading && !items.length}
			<div class="flex flex-col gap-2 px-3">
				<Skeleton class="h-9 w-full" />
				<Skeleton class="h-9 w-5/6" />
				<Skeleton class="h-9 w-2/3" />
			</div>
		{:else if errored && !items.length}
			<Item.Root size="sm">
				<Item.Media><TriangleAlert class="size-4 text-destructive" /></Item.Media>
				<Item.Content>
					<Item.Title>Findings could not be loaded</Item.Title>
				</Item.Content>
				<Item.Actions>
					<Button variant="outline" size="sm" onclick={onRetry}>Retry</Button>
				</Item.Actions>
			</Item.Root>
		{:else}
			<Item.Group class="gap-0.5">
				{#each visible as it (it.key)}
					{@const Icon = it.icon}
					<Item.Root size="sm" class="hover:bg-muted/60">
						{#snippet child({ props })}
							<button type="button" {...props} onclick={() => onFilter(it.filter)}>
								<Item.Media><Icon class="size-4 {TONE_CLASS[it.tone]}" /></Item.Media>
								<Item.Content>
									<Item.Title class="font-normal">{it.text}</Item.Title>
								</Item.Content>
								<Item.Actions>
									<ChevronRight class="size-4 text-muted-foreground/60" />
								</Item.Actions>
							</button>
						{/snippet}
					</Item.Root>
				{/each}
				{#if live && !assessed}
					<Item.Root size="sm">
						<Item.Media><ShieldCheck class="size-4 text-muted-foreground" /></Item.Media>
						<Item.Content>
							<Item.Title class="font-normal text-muted-foreground">
								Exposure checks start once HTTP probing completes
							</Item.Title>
						</Item.Content>
					</Item.Root>
				{:else if !assessed}
					<Item.Root size="sm">
						<Item.Media><ShieldOff class="size-4 text-muted-foreground" /></Item.Media>
						<Item.Content>
							<Item.Title class="font-normal">Exposure checks not performed</Item.Title>
							<Item.Description class="text-xs">
								{scan.status === 'completed'
									? 'This engine does not probe HTTP services.'
									: 'The scan stopped before HTTP probing.'}
							</Item.Description>
						</Item.Content>
						<Item.Actions>
							<Button variant="outline" size="sm" onclick={onRescan}>Re-scan</Button>
						</Item.Actions>
					</Item.Root>
				{:else if !attention.length}
					<Item.Root size="sm">
						<Item.Media><ShieldCheck class="size-4 text-success" /></Item.Media>
						<Item.Content>
							<Item.Title class="font-normal">Nothing flagged</Item.Title>
							<Item.Description class="text-xs">
								Certificates, WAF coverage, server errors, login panels and exposed services were
								checked.
							</Item.Description>
						</Item.Content>
					</Item.Root>
				{/if}
			</Item.Group>
			{#if hidden > 0}
				<Button variant="ghost" size="sm" class="mt-1 ml-3" onclick={() => (expanded = true)}>
					Show {hidden} more
				</Button>
			{/if}
		{/if}
	</Card.Content>
</Card.Root>
