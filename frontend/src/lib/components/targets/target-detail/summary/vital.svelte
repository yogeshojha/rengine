<script lang="ts">
	import type { Vital, Tone, VitalIcon } from './derive';
	import CopyButton from '$lib/components/copy-button.svelte';
	import {
		Route,
		Server,
		Globe,
		Building2,
		CalendarClock,
		Shield,
		Mail,
		Hash,
		Network,
		MapPin,
		Fingerprint,
		Radio,
		Lock,
		Flag
	} from 'lucide-svelte';

	let { vital }: { vital: Vital } = $props();

	const ICONS: Record<VitalIcon, typeof Route> = {
		route: Route,
		server: Server,
		globe: Globe,
		building: Building2,
		calendar: CalendarClock,
		shield: Shield,
		mail: Mail,
		hash: Hash,
		network: Network,
		mappin: MapPin,
		fingerprint: Fingerprint,
		radio: Radio,
		lock: Lock,
		flag: Flag
	};

	const TONE_TEXT: Record<Tone, string> = {
		neutral: 'text-foreground',
		good: 'text-foreground',
		warn: 'text-amber-600 dark:text-amber-500',
		bad: 'text-destructive',
		info: 'text-chart-1'
	};

	const Icon = $derived(vital.icon ? ICONS[vital.icon] : null);
	const toneCls = $derived(TONE_TEXT[vital.tone ?? 'neutral']);
</script>

<div class="group/vital rounded-lg border bg-card px-3 py-2.5 min-w-0">
	<div class="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/70">
		{#if Icon}<Icon class="h-3 w-3 shrink-0 text-muted-foreground/50" />{/if}
		<span class="truncate">{vital.label}</span>
	</div>
	<div class="mt-1 flex items-center gap-1">
		<span class="text-sm font-semibold leading-tight truncate {toneCls} {vital.mono ? 'font-mono text-[13px]' : ''}">
			{vital.value}
		</span>
		{#if vital.copy}
			<div class="opacity-0 group-hover/vital:opacity-100 transition-opacity shrink-0">
				<CopyButton value={vital.copy} />
			</div>
		{/if}
	</div>
	{#if vital.sub}
		<p class="mt-0.5 text-[10px] text-muted-foreground/50 truncate">{vital.sub}</p>
	{/if}
</div>
