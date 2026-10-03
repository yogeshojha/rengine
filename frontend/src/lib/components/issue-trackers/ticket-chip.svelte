<script lang="ts">
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import Hint from '$lib/components/hint.svelte';
	import { externalHref } from '$lib/utilities/links';
	import {
		FILING_STATE_LABELS,
		FilingState,
		REMOTE_CATEGORY_DOT,
		REMOTE_CATEGORY_LABELS,
		RemoteCategory,
		shortKey
	} from '$lib/config/issue-trackers';

	interface Props {
		state: string;
		externalKey: string | null;
		url: string | null;
		remoteStatus: string | null;
		remoteCategory: string | null;
		error?: string | null;
		trackerName?: string;
		compact?: boolean;
	}

	let {
		state,
		externalKey,
		url,
		remoteStatus,
		remoteCategory,
		error = null,
		trackerName = '',
		compact = false
	}: Props = $props();

	const filed = $derived(state === FilingState.FILED);
	const dot = $derived(
		filed
			? (REMOTE_CATEGORY_DOT[remoteCategory as RemoteCategory] ?? 'bg-muted-foreground/30')
			: state === FilingState.FAILED
				? 'bg-destructive'
				: 'bg-muted-foreground/40'
	);
	const label = $derived(
		filed
			? (remoteStatus ?? REMOTE_CATEGORY_LABELS[remoteCategory as RemoteCategory] ?? '')
			: (FILING_STATE_LABELS[state as FilingState] ?? state)
	);
	const hint = $derived(
		state === FilingState.FAILED
			? (error ?? '')
			: [trackerName, externalKey && shortKey(externalKey) !== externalKey ? externalKey : '']
					.filter(Boolean)
					.join(' · ')
	);
</script>

<Hint text={hint}>
	{#snippet child(props)}
		<span {...props} class="inline-flex min-w-0 items-center gap-1.5 text-xs leading-5">
			<span class="flex h-5 shrink-0 items-center">
				<span class="size-2 rounded-full {dot}" aria-hidden="true"></span>
			</span>
			{#if filed && externalKey && url}
				<a
					href={externalHref(url)}
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex min-w-0 items-center gap-1 font-mono wrap-anywhere hover:text-primary"
				>
					{shortKey(externalKey)}
					<ExternalLinkIcon class="size-3 shrink-0 text-muted-foreground" />
				</a>
			{:else if filed && externalKey}
				<span class="font-mono wrap-anywhere">{shortKey(externalKey)}</span>
			{/if}
			{#if !compact || !filed}
				<span
					class={filed
						? 'text-muted-foreground'
						: state === FilingState.FAILED
							? 'text-destructive'
							: 'text-muted-foreground'}
				>
					{label}
				</span>
			{/if}
		</span>
	{/snippet}
</Hint>
