<script lang="ts">
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge';
	import Hint from '$lib/components/hint.svelte';
	import { SIGNAL_ICONS, SIGNAL_LABELS, SIGNAL_QUERY } from '$lib/config/threat-intel';

	interface Props {
		kind: string;
		reason?: string;
		compact?: boolean;
		onFilter?: (token: string) => void;
	}

	let { kind, reason = '', compact = false, onFilter }: Props = $props();

	let Icon = $derived(SIGNAL_ICONS[kind]);
	let label = $derived(SIGNAL_LABELS[kind] ?? kind);
	let token = $derived(SIGNAL_QUERY[kind] ?? '');
	let variant = $derived<BadgeVariant>(
		kind === 'kev' || kind === 'ransom_path' || kind === 'ransomware' || kind === 'fresh_exploit'
			? 'destructive'
			: kind === 'overdue' || kind === 'weaponised' || kind === 'likely'
				? 'warning'
				: 'secondary'
	);
</script>

<Hint text={reason || label}>
	{#snippet child(props)}
		<button
			{...props}
			type="button"
			class="flex h-5 shrink-0 items-center"
			disabled={!onFilter}
			onclick={(e) => {
				e.stopPropagation();
				onFilter?.(token);
			}}
			aria-label={label}
		>
			<Badge {variant} class="gap-1 px-1.5 text-[10px] font-normal">
				{#if Icon}<Icon class="size-2.5" />{/if}
				{#if !compact}{label}{/if}
			</Badge>
		</button>
	{/snippet}
</Hint>
