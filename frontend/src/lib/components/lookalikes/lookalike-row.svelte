<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Copy from '@lucide/svelte/icons/copy';
	import Check from '@lucide/svelte/icons/check';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import { toast } from 'svelte-sonner';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import LookalikeName from './lookalike-name.svelte';
	import { SEVERITY_CHIP } from '$lib/config/vulnerabilities';
	import {
		LINK_LABELS,
		LookalikeState,
		SIMILAR_AT,
		VERDICT_BY_KEY,
		brandOf,
		brandSegments,
		techniqueLabel
	} from '$lib/config/lookalikes';
	import { MS_PER_DAY, formatDateTime, relativeTime } from '$lib/utilities/dates';
	import type { LookalikeRead } from '$lib/types/lookalike';

	interface Props {
		row: LookalikeRead;
		onReview: (next: LookalikeState) => void;
	}

	let { row, onReview }: Props = $props();

	const RECENT_DAYS = 30;

	let open = $state(false);
	let spec = $derived(VERDICT_BY_KEY[row.verdict]);
	let tone = $derived(spec ? SEVERITY_CHIP[spec.severity] : null);
	let recent = $derived(
		!!row.registered_at &&
			Date.now() - new Date(row.registered_at).getTime() < RECENT_DAYS * MS_PER_DAY
	);
	let addresses = $derived([...row.a, ...row.aaaa]);
	let title = $derived(row.title ? brandSegments(row.title, brandOf(row.apex)) : []);

	async function copy(value: string) {
		if (await writeClipboard(value)) toast.success('Domain copied');
		else toast.error('Domain not copied');
	}

	const more = (list: string[]) => (list.length > 1 ? ` +${list.length - 1}` : '');
</script>

<li class="relative">
	<span class="absolute top-3 bottom-3 left-0 w-0.5 rounded-full {tone?.edge ?? 'bg-border'}"
	></span>
	<div class="flex items-start gap-3 py-3 pr-3 pl-4">
		<div class="flex min-w-0 flex-1 flex-col gap-1.5">
			<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
				<LookalikeName
					display={row.display}
					domain={row.domain}
					apex={row.apex}
					class="text-sm leading-5 font-medium"
				/>
				{#if spec && tone}
					<Hint text={spec.help}>
						{#snippet child(props)}
							<span
								{...props}
								class="inline-flex h-5 items-center rounded-sm px-1.5 text-2xs font-medium {tone.chip}"
							>
								{spec.label}
							</span>
						{/snippet}
					</Hint>
				{/if}
			</div>
			<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
				<span>{techniqueLabel(row.technique)}</span>
				{#if row.registered_at}
					<span class={recent ? 'font-medium text-warning' : ''}>
						Registered {relativeTime(row.registered_at)}
					</span>
				{/if}
				{#if row.link_reason}
					<span>{LINK_LABELS[row.link_reason] ?? row.link_reason}</span>
				{/if}
				{#if row.mx.length}
					<span class="font-mono">MX {row.mx[0]}{more(row.mx)}</span>
				{/if}
				{#if addresses.length}
					<span class="font-mono">{addresses[0]}{more(addresses)}</span>
				{/if}
				{#if row.title}
					<span class="max-w-72 truncate">
						{#each title as t, i (i)}{#if t.changed}<mark
									class="rounded-[3px] bg-sev-high-wash px-px font-medium text-sev-high-ink"
									>{t.text}</mark
								>{:else}{t.text}{/if}{/each}
					</span>
				{/if}
			</div>
		</div>

		{#if row.similarity != null}
			<Hint text="Page similarity to the target's page">
				{#snippet child(props)}
					<span {...props} class="flex h-5 shrink-0 items-center gap-2">
						<span class="h-1.5 w-14 overflow-hidden rounded-full bg-muted">
							<span
								class="block h-full rounded-full {row.similarity! >= SIMILAR_AT
									? 'bg-sev-critical'
									: 'bg-muted-foreground/40'}"
								style="width:{Math.max(4, row.similarity!)}%"
							></span>
						</span>
						<span class="w-8 text-right text-xs font-medium tabular-nums">{row.similarity}%</span>
					</span>
				{/snippet}
			</Hint>
		{/if}

		<span class="flex h-5 shrink-0 items-center gap-0.5">
			<Button
				variant="ghost"
				size="icon"
				class="size-7"
				aria-expanded={open}
				aria-label="{open ? 'Hide' : 'Show'} records for {row.display}"
				onclick={() => (open = !open)}
			>
				<ChevronDown class="size-4 transition-transform {open ? 'rotate-180' : ''}" />
			</Button>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="ghost" size="icon" class="size-7">
							<Ellipsis class="size-4" />
							<span class="sr-only">Actions for {row.display}</span>
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-48">
					{#if row.state !== LookalikeState.REVIEWED}
						<DropdownMenu.Item onclick={() => onReview(LookalikeState.REVIEWED)}>
							<Check class="size-3.5" /> Mark reviewed
						</DropdownMenu.Item>
					{/if}
					{#if row.state !== LookalikeState.IGNORED}
						<DropdownMenu.Item onclick={() => onReview(LookalikeState.IGNORED)}>
							<EyeOff class="size-3.5" /> Ignore
						</DropdownMenu.Item>
					{/if}
					{#if row.state !== LookalikeState.OPEN}
						<DropdownMenu.Item onclick={() => onReview(LookalikeState.OPEN)}>
							<RotateCcw class="size-3.5" /> Reopen
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Item onclick={() => copy(row.domain)}>
						<Copy class="size-3.5" /> Copy domain
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</span>
	</div>

	{#if open}
		<dl
			class="mx-4 mb-3 grid grid-cols-[7rem_1fr] gap-x-4 gap-y-1.5 rounded-md border bg-muted/30 px-3 py-2.5 text-xs"
		>
			{#snippet list(label: string, values: string[])}
				{#if values.length}
					<dt class="text-muted-foreground">{label}</dt>
					<dd class="font-mono break-all">{values.join(', ')}</dd>
				{/if}
			{/snippet}
			{@render list('Addresses', addresses)}
			{@render list('Mail servers', row.mx)}
			{@render list('Nameservers', row.ns)}
			{#if row.http_status != null}
				<dt class="text-muted-foreground">HTTP response</dt>
				<dd class="font-mono break-all">
					{row.http_status}{#if row.final_url}&nbsp;{row.final_url}{/if}
				</dd>
			{/if}
			{#if row.title}
				<dt class="text-muted-foreground">Title</dt>
				<dd class="break-all">{row.title}</dd>
			{/if}
			{#if row.registrar}
				<dt class="text-muted-foreground">Registrar</dt>
				<dd>{row.registrar}</dd>
			{/if}
			{#if row.registered_at}
				<dt class="text-muted-foreground">Registered</dt>
				<dd>{formatDateTime(row.registered_at)}</dd>
			{/if}
			<dt class="text-muted-foreground">First seen</dt>
			<dd>{formatDateTime(row.first_seen)}</dd>
		</dl>
	{/if}
</li>
