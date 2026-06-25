<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import Star from '@lucide/svelte/icons/star';
	import * as Table from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import ScreenshotThumb from './screenshot-thumb.svelte';
	import TechBadges from './tech-badges.svelte';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import { formatBytes, httpStatusTextClass } from '$lib/utilities/scan-correlation';

	interface Props {
		subdomains: SubdomainRead[];
	}

	let { subdomains }: Props = $props();

	let search = $state('');
	let liveOnly = $state(false);
	let httpOnly = $state(false);

	const MAX_SOURCES = 3;

	let filtered = $derived.by(() => {
		const q = search.trim().toLowerCase();
		return subdomains.filter((s) => {
			if (liveOnly && !s.is_active) return false;
			if (httpOnly && !s.http_status) return false;
			if (!q) return true;
			return (
				s.name.toLowerCase().includes(q) ||
				(s.page_title ?? '').toLowerCase().includes(q) ||
				(s.webserver ?? '').toLowerCase().includes(q) ||
				s.resolved_ips.some((ip) => ip.includes(q)) ||
				s.tech.some((t) => t.toLowerCase().includes(q))
			);
		});
	});
</script>

<div class="space-y-3">
	<div class="flex flex-wrap items-center gap-2">
		<div class="relative min-w-[200px] flex-1">
			<Search
				class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
			/>
			<Input
				bind:value={search}
				placeholder="Filter subdomain, title, tech, IP…"
				class="h-8 pl-8 text-sm"
			/>
		</div>
		<Button
			size="sm"
			variant={liveOnly ? 'default' : 'outline'}
			class="h-8 px-2.5"
			onclick={() => (liveOnly = !liveOnly)}
		>
			Live only
		</Button>
		<Button
			size="sm"
			variant={httpOnly ? 'default' : 'outline'}
			class="h-8 px-2.5"
			onclick={() => (httpOnly = !httpOnly)}
		>
			Has web
		</Button>
	</div>

	<div class="text-xs text-muted-foreground">
		Showing {filtered.length} of {subdomains.length}
	</div>

	<div class="rounded-lg border border-border">
		<Table.Root>
			<Table.Header>
				<Table.Row>
					<Table.Head class="w-[88px]"></Table.Head>
					<Table.Head>Subdomain</Table.Head>
					<Table.Head class="w-[60px]">Status</Table.Head>
					<Table.Head>Title</Table.Head>
					<Table.Head>Tech</Table.Head>
					<Table.Head>Resolved IPs</Table.Head>
					<Table.Head>Sources</Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each filtered as s (s.id)}
					<Table.Row>
						<Table.Cell>
							<ScreenshotThumb path={s.screenshot_path} alt={s.name} class="h-10 w-16" />
						</Table.Cell>
						<Table.Cell>
							<div class="flex items-center gap-1.5 font-mono text-xs">
								{#if s.is_important}<Star class="h-3 w-3 fill-warning text-warning" />{/if}
								{s.name}
							</div>
							<div class="mt-0.5 flex gap-1">
								{#if s.is_wildcard}<Badge
										variant="outline"
										class="px-1 py-0 text-[10px] font-normal text-warning">wildcard</Badge
									>{/if}
								{#if s.is_excluded}<Badge
										variant="outline"
										class="px-1 py-0 text-[10px] font-normal text-warning">excluded</Badge
									>{/if}
								{#if !s.is_active}<Badge
										variant="outline"
										class="px-1 py-0 text-[10px] font-normal text-muted-foreground">inactive</Badge
									>{/if}
								{#if s.is_cdn}<Badge variant="info" class="px-1 py-0 text-[10px] font-normal"
										>CDN</Badge
									>{/if}
							</div>
						</Table.Cell>
						<Table.Cell>
							{#if s.http_status}
								<span class="font-mono text-xs font-medium {httpStatusTextClass(s.http_status)}">
									{s.http_status}
								</span>
							{:else}
								<span class="text-xs text-muted-foreground">—</span>
							{/if}
						</Table.Cell>
						<Table.Cell class="max-w-[220px]">
							<div class="truncate text-xs" title={s.page_title ?? ''}>{s.page_title ?? '—'}</div>
							<div class="truncate text-[11px] text-muted-foreground">
								{[s.webserver, s.content_length != null ? formatBytes(s.content_length) : null]
									.filter(Boolean)
									.join(' · ') || ''}
							</div>
						</Table.Cell>
						<Table.Cell><TechBadges tech={s.tech} max={3} /></Table.Cell>
						<Table.Cell class="font-mono text-[11px] text-muted-foreground">
							{s.resolved_ips.length ? s.resolved_ips.slice(0, 2).join(', ') : '—'}
							{#if s.resolved_ips.length > 2}<span class="text-muted-foreground/70">
									+{s.resolved_ips.length - 2}</span
								>{/if}
						</Table.Cell>
						<Table.Cell>
							<div class="flex flex-wrap gap-1">
								{#each s.sources.slice(0, MAX_SOURCES) as src (src)}
									<Badge variant="outline" class="px-1 py-0 text-[10px] font-normal">{src}</Badge>
								{/each}
								{#if s.sources.length > MAX_SOURCES}
									<Badge
										variant="outline"
										class="px-1 py-0 text-[10px] font-normal text-muted-foreground"
									>
										+{s.sources.length - MAX_SOURCES}
									</Badge>
								{/if}
							</div>
						</Table.Cell>
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
	</div>
</div>
