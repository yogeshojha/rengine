<script lang="ts">
	import FileCode from '@lucide/svelte/icons/file-code';
	import ListTree from '@lucide/svelte/icons/list-tree';
	import Lock from '@lucide/svelte/icons/lock';
	import CornerDownRight from '@lucide/svelte/icons/corner-down-right';
	import Route from '@lucide/svelte/icons/route';
	import Image from '@lucide/svelte/icons/image';
	import Building2 from '@lucide/svelte/icons/building-2';
	import Server from '@lucide/svelte/icons/server';
	import Link from '@lucide/svelte/icons/link';
	import Network from '@lucide/svelte/icons/network';
	import Layers from '@lucide/svelte/icons/layers';
	import Radar from '@lucide/svelte/icons/radar';
	import Type from '@lucide/svelte/icons/type';
	import Globe from '@lucide/svelte/icons/globe';
	import Hash from '@lucide/svelte/icons/hash';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { stopProp } from '$lib/utilities';
	import type { IconComponent } from '$lib/config/icons';
	import type { MatchEvidence } from '$lib/types/asset-query';
	import HighlightText from './highlight-text.svelte';

	interface Props {
		matches: MatchEvidence[];
		suppress: Set<string>;
		onOpen: (field: string) => void;
	}

	let { matches, suppress, onOpen }: Props = $props();

	const MAX_CHIPS = 3;
	const ICONS: Record<string, IconComponent> = {
		body: FileCode,
		header: ListTree,
		cert: Lock,
		redirect: CornerDownRight,
		path: Route,
		favicon: Image,
		org: Building2,
		server: Server,
		url: Link,
		ip: Network,
		tech: Layers,
		source: Radar,
		cname: CornerDownRight,
		title: Type,
		host: Globe,
		content_type: Hash,
		cdn: Network,
		waf: Lock
	};
	const ORDER = [
		'body',
		'header',
		'cert',
		'redirect',
		'path',
		'favicon',
		'cname',
		'source',
		'org',
		'server',
		'url',
		'ip',
		'content_type',
		'cdn',
		'waf',
		'tech',
		'title',
		'host'
	];

	const rank = (field: string) => {
		const at = ORDER.indexOf(field);
		return at === -1 ? ORDER.length : at;
	};

	let ordered = $derived(
		matches.filter((m) => !suppress.has(m.field)).sort((a, b) => rank(a.field) - rank(b.field))
	);
	let shown = $derived(ordered.slice(0, MAX_CHIPS));
	let rest = $derived(ordered.slice(MAX_CHIPS));
</script>

{#snippet detail(match: MatchEvidence)}
	<p class="text-xs font-medium">{match.label} contains “{match.term}”</p>
	{#if match.snippet}
		<p
			class="mt-1.5 max-h-32 overflow-hidden rounded border border-border bg-accent/50 p-2 font-mono text-[11px] leading-relaxed break-all text-muted-foreground"
		>
			<HighlightText text={match.snippet} term={match.term} />
		</p>
	{/if}
{/snippet}

{#if ordered.length}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="flex flex-wrap items-center gap-1" onclick={stopProp}>
		<span class="text-[10px] text-muted-foreground/70">matched in</span>
		{#each shown as match (match.field + match.term)}
			{@const Icon = ICONS[match.field] ?? Hash}
			<HoverCard.Root openDelay={120}>
				<HoverCard.Trigger>
					{#snippet child({ props })}
						<button
							{...props}
							type="button"
							class="inline-flex items-center gap-1 rounded border border-primary/25 bg-primary/5 px-1.5 py-px text-[10px] font-medium text-primary/90 hover:bg-primary/10"
							onclick={() => onOpen(match.field)}
						>
							<Icon class="size-2.5" />
							{match.label}
						</button>
					{/snippet}
				</HoverCard.Trigger>
				<HoverCard.Content class="w-96 max-w-[90vw] p-3" side="top" align="start">
					{@render detail(match)}
					<p class="mt-1.5 text-[11px] text-muted-foreground">Click to open the evidence.</p>
				</HoverCard.Content>
			</HoverCard.Root>
		{/each}
		{#if rest.length}
			<HoverCard.Root openDelay={120}>
				<HoverCard.Trigger>
					{#snippet child({ props })}
						<span
							{...props}
							class="rounded border border-border px-1.5 py-px text-[10px] text-muted-foreground"
						>
							+{rest.length}
						</span>
					{/snippet}
				</HoverCard.Trigger>
				<HoverCard.Content
					class="flex w-96 max-w-[90vw] flex-col gap-3 p-3"
					side="top"
					align="start"
				>
					{#each rest as match (match.field + match.term)}
						<button type="button" class="text-left" onclick={() => onOpen(match.field)}>
							{@render detail(match)}
						</button>
					{/each}
				</HoverCard.Content>
			</HoverCard.Root>
		{/if}
	</div>
{/if}
