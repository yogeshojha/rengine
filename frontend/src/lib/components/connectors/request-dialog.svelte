<script lang="ts">
	import RadarIcon from '@lucide/svelte/icons/radar';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import ListTreeIcon from '@lucide/svelte/icons/list-tree';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import LockIcon from '@lucide/svelte/icons/lock';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import CopyButton from '$lib/components/copy-button.svelte';
	import CodeBlock from '$lib/components/code-block.svelte';
	import ProxySend from '$lib/components/scans/results/endpoints/proxy-send.svelte';
	import { connectors } from '$lib/stores/connectors.svelte';
	import {
		CANDIDATE_STATE_LABELS,
		NOTICE_HELP,
		NOTICE_LABELS,
		SOURCE_TOOL_LABELS,
		noticeTone,
		type ActionKind
	} from '$lib/config/connectors';
	import { relativeTime } from '$lib/utilities/dates';
	import { httpStatusTextClass } from '$lib/utilities/scan-correlation';
	import type { Candidate, Connector, HandoffResult } from '$lib/types/connector';

	interface Props {
		row: Candidate | null;
		connector: Connector;
		endpointsHref: string | null;
		onClose: () => void;
		onSend: (kind: ActionKind, request?: string) => Promise<HandoffResult | null> | null;
		onPreview: () => Promise<string | null>;
		onScan: (row: Candidate) => void;
		onIgnore: (row: Candidate) => void;
	}

	let { row, connector, endpointsHref, onClose, onSend, onPreview, onScan, onIgnore }: Props =
		$props();

	const LABEL = 'text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase';
</script>

<Dialog.Root
	open={row !== null}
	onOpenChange={(v) => {
		if (!v) onClose();
	}}
>
	<Dialog.Content class="gap-0 p-0 sm:max-w-2xl" onOpenAutoFocus={(e) => e.preventDefault()}>
		{#if row}
			<Dialog.Header class="gap-2 border-b px-6 py-4">
				<Dialog.Title class="flex min-w-0 items-center gap-2.5 pr-8 font-mono text-sm">
					<span class="text-muted-foreground shrink-0">{row.methods.join(' ') || 'GET'}</span>
					<span class="min-w-0 wrap-anywhere">{row.path}</span>
				</Dialog.Title>
				<div class="flex min-w-0 items-center gap-2">
					<span class="text-muted-foreground min-w-0 truncate font-mono text-xs">{row.url}</span>
					<CopyButton value={row.url} class="size-6 shrink-0" />
				</div>
			</Dialog.Header>

			<div class="flex flex-col gap-5 px-6 py-5">
				<dl class="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
					<div>
						<dt class={LABEL}>Status</dt>
						<dd class="mt-1 font-mono tabular-nums {httpStatusTextClass(row.status_code)}">
							{row.status_code ?? '—'}
						</dd>
					</div>
					<div>
						<dt class={LABEL}>Requests</dt>
						<dd class="mt-1 tabular-nums">{row.hits.toLocaleString()}</dd>
					</div>
					<div>
						<dt class={LABEL}>Source</dt>
						<dd class="mt-1">{SOURCE_TOOL_LABELS[row.source_tool] ?? row.source_tool}</dd>
					</div>
					<div>
						<dt class={LABEL}>State</dt>
						<dd class="mt-1">{CANDIDATE_STATE_LABELS[row.state]}</dd>
					</div>
					<div>
						<dt class={LABEL}>First seen</dt>
						<dd class="mt-1">{relativeTime(row.first_seen_at)}</dd>
					</div>
					<div>
						<dt class={LABEL}>Last seen</dt>
						<dd class="mt-1">{relativeTime(row.last_seen_at)}</dd>
					</div>
					<div>
						<dt class={LABEL}>Scans</dt>
						<dd class="mt-1">{row.known ? 'Recorded' : 'Not recorded'}</dd>
					</div>
					<div>
						<dt class={LABEL}>Session</dt>
						<dd class="mt-1 flex items-center gap-1.5">
							{#if row.authenticated}
								<LockIcon class="text-muted-foreground size-3" /> Present
							{:else}
								None
							{/if}
						</dd>
					</div>
				</dl>

				{#if row.notices.length}
					<div class="flex flex-col gap-2">
						<span class={LABEL}>Notices</span>
						<ul class="flex flex-col gap-1.5">
							{#each row.notices as item (item)}
								<li class="text-sm">
									<span class={noticeTone(item)}>{NOTICE_LABELS[item] ?? item}</span>
									{#if NOTICE_HELP[item]}
										<span class="text-muted-foreground"> · {NOTICE_HELP[item]}</span>
									{/if}
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				{#if row.params.length}
					<div class="flex flex-col gap-2">
						<span class={LABEL}>Parameters</span>
						<div class="flex flex-wrap gap-1.5">
							{#each row.params as param (param)}
								<code class="bg-muted rounded px-1.5 py-0.5 font-mono text-xs">{param}</code>
							{/each}
						</div>
					</div>
				{/if}

				{#if row.request_sample}
					<div class="flex flex-col gap-2">
						<span class={LABEL}>Request</span>
						<CodeBlock code={row.request_sample} lang="http" maxLines={14} />
					</div>
				{/if}
			</div>

			<div
				class="flex flex-wrap items-center justify-between gap-2 border-t bg-muted/30 px-6 py-3.5"
			>
				<div class="flex items-center gap-1">
					{#if endpointsHref}
						<Button variant="ghost" size="sm" href={endpointsHref}>
							<ListTreeIcon class="size-3.5" /> Endpoints
						</Button>
					{/if}
					<Button
						variant="ghost"
						size="sm"
						href={row.url}
						target="_blank"
						rel="noopener noreferrer"
					>
						<ExternalLinkIcon class="size-3.5" /> Open
					</Button>
				</div>
				<div class="flex items-center gap-2">
					<Button variant="outline" size="sm" onclick={() => onIgnore(row)}>
						<EyeOffIcon class="size-3.5" /> Ignore
					</Button>
					<Button variant="outline" size="sm" onclick={() => onScan(row)}>
						<RadarIcon class="size-3.5" /> Scan
					</Button>
					{#if !connector.paused}
						<ProxySend
							connectors={[connector]}
							catalog={connectors.catalog}
							class="h-8"
							onSend={(_id, kind, request) => onSend(kind, request)}
							onPreview={() => onPreview()}
						/>
					{/if}
				</div>
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
