<script lang="ts">
	import * as Table from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { relativeTime } from '$lib/utilities/dates';

	interface Row {
		name: string;
		sources: string[];
		resolved_ips: string[];
		is_active: boolean;
		is_wildcard: boolean;
		is_excluded?: boolean;
		last_seen: string;
		scan_count?: number;
	}

	interface Props {
		rows: Row[];
		showScans?: boolean;
	}

	let { rows, showScans = false }: Props = $props();

	const MAX_SOURCES = 4;
</script>

<div class="rounded-lg border border-border">
	<Table.Root>
		<Table.Header>
			<Table.Row>
				<Table.Head>Subdomain</Table.Head>
				<Table.Head>Resolved IPs</Table.Head>
				<Table.Head>Sources</Table.Head>
				<Table.Head>Status</Table.Head>
				{#if showScans}<Table.Head class="text-right">Scans</Table.Head>{/if}
				<Table.Head class="text-right">Last seen</Table.Head>
			</Table.Row>
		</Table.Header>
		<Table.Body>
			{#each rows as row (row.name)}
				<Table.Row>
					<Table.Cell class="font-mono text-xs">
						{row.name}
						{#if row.is_wildcard}
							<Badge variant="outline" class="ml-1.5 font-normal text-warning">wildcard</Badge>
						{/if}
					</Table.Cell>
					<Table.Cell class="font-mono text-xs text-muted-foreground">
						{row.resolved_ips.length ? row.resolved_ips.join(', ') : '—'}
					</Table.Cell>
					<Table.Cell>
						<div class="flex flex-wrap gap-1">
							{#each row.sources.slice(0, MAX_SOURCES) as src (src)}
								<Badge variant="outline" class="font-normal">{src}</Badge>
							{/each}
							{#if row.sources.length > MAX_SOURCES}
								<Badge variant="outline" class="font-normal text-muted-foreground">
									+{row.sources.length - MAX_SOURCES}
								</Badge>
							{/if}
						</div>
					</Table.Cell>
					<Table.Cell>
						{#if row.is_excluded}
							<Badge variant="outline" class="font-normal text-warning">Excluded</Badge>
						{:else if row.is_active}
							<Badge variant="secondary" class="font-normal">Live</Badge>
						{:else}
							<span class="text-xs text-muted-foreground">Inactive</span>
						{/if}
					</Table.Cell>
					{#if showScans}
						<Table.Cell class="text-right text-xs text-muted-foreground">
							{row.scan_count ?? 1}
						</Table.Cell>
					{/if}
					<Table.Cell class="text-right text-xs text-muted-foreground">
						{relativeTime(row.last_seen)}
					</Table.Cell>
				</Table.Row>
			{/each}
		</Table.Body>
	</Table.Root>
</div>
