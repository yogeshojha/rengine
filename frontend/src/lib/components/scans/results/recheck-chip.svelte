<script lang="ts">
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Hint from '$lib/components/hint.svelte';
	import { cn } from '$lib/utils';
	import type { Recheck } from '$lib/types/recheck';
	import { relativeTime } from '$lib/utilities/dates';
	import { isRecheckLive, recheckLabel, recheckTone } from '$lib/utilities/rechecks';

	interface Props {
		recheck: Recheck | null;
		onclick?: () => void;
		class?: string;
	}

	let { recheck, onclick, class: className }: Props = $props();

	let tone = $derived(recheck ? recheckTone(recheck) : 'quiet');
	let live = $derived(!!recheck && isRecheckLive(recheck));
	let when = $derived(recheck && !live ? relativeTime(recheck.created_at) : '');
	let hint = $derived.by(() => {
		if (!recheck) return '';
		if (live) return 'Rechecking now';
		const stages = recheck.stage_titles.join(' · ');
		const changed = recheck.changes.map((c) => c.label).join(', ');
		return [stages, changed && `changed: ${changed}`].filter(Boolean).join(' — ');
	});

	const TONES = {
		live: 'border-primary/40 bg-primary/10 text-primary',
		changed: 'border-primary/40 bg-primary/10 text-primary',
		quiet: 'border-border bg-muted/40 text-muted-foreground',
		failed: 'border-destructive/40 bg-destructive/10 text-destructive'
	};
</script>

{#if recheck}
	<Hint text={hint}>
		{#snippet child(props)}
			<button
				{...props}
				type="button"
				onclick={(e) => {
					e.stopPropagation();
					onclick?.();
				}}
				class={cn(
					'inline-flex shrink-0 items-center gap-1 rounded-full border px-[7px] py-px text-[11px] font-medium whitespace-nowrap transition-colors',
					TONES[tone],
					onclick && 'hover:brightness-95',
					className
				)}
			>
				<RefreshCw class={cn('size-2.5', live && 'animate-spin')} />
				{#if when}<span class="tabular-nums">{when}</span><span class="opacity-40">·</span>{/if}
				<span>{recheckLabel(recheck)}</span>
			</button>
		{/snippet}
	</Hint>
{/if}
