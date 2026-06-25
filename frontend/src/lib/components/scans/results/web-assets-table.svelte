<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import * as Table from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import ScreenshotThumb from './screenshot-thumb.svelte';
	import TechBadges from './tech-badges.svelte';
	import HttpAssetSheet from './http-asset-sheet.svelte';
	import type { HttpAssetRead } from '$lib/types/http-asset';
	import type { IpGroup } from '$lib/utilities/scan-correlation';
	import {
		formatBytes,
		formatResponseTime,
		httpStatusTextClass
	} from '$lib/utilities/scan-correlation';

	interface Props {
		assets: HttpAssetRead[];
		ipGroups: Map<string, IpGroup>;
	}

	let { assets, ipGroups }: Props = $props();

	let search = $state('');
	let statusFilter = $state<'all' | '2' | '3' | '4' | '5'>('all');
	let cdnOnly = $state(false);
	let tlsIssuesOnly = $state(false);
	let selected = $state<HttpAssetRead | null>(null);
	let sheetOpen = $state(false);

	const STATUS_FILTERS: { key: typeof statusFilter; label: string }[] = [
		{ key: 'all', label: 'All' },
		{ key: '2', label: '2xx' },
		{ key: '3', label: '3xx' },
		{ key: '4', label: '4xx' },
		{ key: '5', label: '5xx' }
	];

	let filtered = $derived.by(() => {
		const q = search.trim().toLowerCase();
		return assets.filter((a) => {
			if (statusFilter !== 'all') {
				if (a.status_code == null || Math.floor(a.status_code / 100) !== Number(statusFilter))
					return false;
			}
			if (cdnOnly && !a.is_cdn) return false;
			if (tlsIssuesOnly && !a.tls_expired && !a.tls_self_signed) return false;
			if (!q) return true;
			return (
				a.host.toLowerCase().includes(q) ||
				a.url.toLowerCase().includes(q) ||
				(a.title ?? '').toLowerCase().includes(q) ||
				(a.webserver ?? '').toLowerCase().includes(q) ||
				(a.ip ?? '').includes(q) ||
				a.tech.some((t) => t.toLowerCase().includes(q))
			);
		});
	});

	function open(asset: HttpAssetRead) {
		selected = asset;
		sheetOpen = true;
	}

	let selectedGroup = $derived(selected?.ip ? (ipGroups.get(selected.ip) ?? null) : null);
</script>

<div class="space-y-3">
	<div class="flex flex-wrap items-center gap-2">
		<div class="relative min-w-[200px] flex-1">
			<Search
				class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
			/>
			<Input
				bind:value={search}
				placeholder="Filter host, title, tech, IP…"
				class="h-8 pl-8 text-sm"
			/>
		</div>
		<div class="flex items-center gap-1">
			{#each STATUS_FILTERS as f (f.key)}
				<Button
					size="sm"
					variant={statusFilter === f.key ? 'default' : 'outline'}
					class="h-8 px-2.5"
					onclick={() => (statusFilter = f.key)}
				>
					{f.label}
				</Button>
			{/each}
		</div>
		<Button
			size="sm"
			variant={cdnOnly ? 'default' : 'outline'}
			class="h-8 px-2.5"
			onclick={() => (cdnOnly = !cdnOnly)}
		>
			CDN
		</Button>
		<Button
			size="sm"
			variant={tlsIssuesOnly ? 'default' : 'outline'}
			class="h-8 px-2.5"
			onclick={() => (tlsIssuesOnly = !tlsIssuesOnly)}
		>
			TLS issues
		</Button>
	</div>

	<div class="text-xs text-muted-foreground">
		Showing {filtered.length} of {assets.length}
	</div>

	<div class="rounded-lg border border-border">
		<Table.Root>
			<Table.Header>
				<Table.Row>
					<Table.Head class="w-[88px]"></Table.Head>
					<Table.Head>Host</Table.Head>
					<Table.Head class="w-[60px]">Status</Table.Head>
					<Table.Head>Title</Table.Head>
					<Table.Head>Tech</Table.Head>
					<Table.Head>IP</Table.Head>
					<Table.Head class="text-right">Size</Table.Head>
					<Table.Head class="text-right">Time</Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each filtered as a (a.id)}
					<Table.Row class="cursor-pointer" onclick={() => open(a)}>
						<Table.Cell>
							<ScreenshotThumb
								path={a.screenshot_path}
								alt={a.host}
								interactive={false}
								class="h-10 w-16"
							/>
						</Table.Cell>
						<Table.Cell>
							<div class="font-mono text-xs">{a.host}</div>
							<div class="text-[11px] text-muted-foreground">{a.scheme}://:{a.port}</div>
						</Table.Cell>
						<Table.Cell>
							<span class="font-mono text-xs font-medium {httpStatusTextClass(a.status_code)}">
								{a.status_code ?? '—'}
							</span>
						</Table.Cell>
						<Table.Cell class="max-w-[220px]">
							<div class="truncate text-xs" title={a.title ?? ''}>{a.title ?? '—'}</div>
							{#if a.webserver}
								<div class="truncate text-[11px] text-muted-foreground">{a.webserver}</div>
							{/if}
						</Table.Cell>
						<Table.Cell><TechBadges tech={a.tech} max={3} /></Table.Cell>
						<Table.Cell>
							<div class="font-mono text-xs text-muted-foreground">{a.ip ?? '—'}</div>
							<div class="mt-0.5 flex gap-1">
								{#if a.is_cdn}<Badge variant="info" class="px-1 py-0 text-[10px] font-normal"
										>CDN</Badge
									>{/if}
								{#if a.waf}<Badge variant="warning" class="px-1 py-0 text-[10px] font-normal"
										>WAF</Badge
									>{/if}
								{#if a.tls_expired}<Badge
										variant="destructive"
										class="px-1 py-0 text-[10px] font-normal">TLS</Badge
									>{/if}
							</div>
						</Table.Cell>
						<Table.Cell class="text-right font-mono text-[11px] text-muted-foreground">
							{formatBytes(a.content_length)}
						</Table.Cell>
						<Table.Cell class="text-right font-mono text-[11px] text-muted-foreground">
							{formatResponseTime(a.response_time)}
						</Table.Cell>
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
	</div>
</div>

<HttpAssetSheet
	asset={selected}
	ipMeta={selectedGroup?.meta ?? null}
	ports={selectedGroup?.ports ?? []}
	neighbors={selectedGroup?.hosts ?? []}
	open={sheetOpen}
	onOpenChange={(o) => (sheetOpen = o)}
/>
