<script lang="ts">
	import type { Vital, Tone, VitalIcon } from './derive';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Route from '@lucide/svelte/icons/route';
	import Server from '@lucide/svelte/icons/server';
	import Globe from '@lucide/svelte/icons/globe';
	import Building2 from '@lucide/svelte/icons/building-2';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Shield from '@lucide/svelte/icons/shield';
	import Mail from '@lucide/svelte/icons/mail';
	import Hash from '@lucide/svelte/icons/hash';
	import Network from '@lucide/svelte/icons/network';
	import MapPin from '@lucide/svelte/icons/map-pin';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import Radio from '@lucide/svelte/icons/radio';
	import Lock from '@lucide/svelte/icons/lock';
	import Flag from '@lucide/svelte/icons/flag';

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
		warn: 'text-warning',
		bad: 'text-destructive',
		info: 'text-chart-1'
	};

	const Icon = $derived(vital.icon ? ICONS[vital.icon] : null);
	const toneCls = $derived(TONE_TEXT[vital.tone ?? 'neutral']);
</script>

<div class="group/vital rounded-lg border bg-card px-3 py-2.5 min-w-0">
	<div
		class="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/70"
	>
		{#if Icon}<Icon class="h-3 w-3 shrink-0 text-muted-foreground/50" />{/if}
		<span class="truncate">{vital.label}</span>
	</div>
	<div class="mt-1 flex items-center gap-1">
		<span
			class="text-sm font-semibold leading-tight truncate {toneCls} {vital.mono
				? 'font-mono text-[13px]'
				: ''}"
		>
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
