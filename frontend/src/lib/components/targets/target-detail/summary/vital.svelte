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
	import type { IconComponent } from '$lib/config/icons';

	let { vital }: { vital: Vital } = $props();

	const ICONS: Record<VitalIcon, IconComponent> = {
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
		info: 'text-foreground'
	};

	const Icon = $derived(vital.icon ? ICONS[vital.icon] : null);
	const toneCls = $derived(TONE_TEXT[vital.tone ?? 'neutral']);
</script>

<div class="group/vital flex min-w-0 flex-col gap-1.5 border-t border-l px-5 py-4">
	<span class="flex items-center gap-1.5 text-xs text-muted-foreground">
		{#if Icon}
			<span class="flex h-4 shrink-0 items-center">
				<Icon class="size-3.5" />
			</span>
		{/if}
		<span class="truncate">{vital.label}</span>
	</span>
	<span class="flex min-w-0 items-center gap-1">
		<span class="truncate text-sm leading-5 font-medium {toneCls} {vital.mono ? 'font-mono' : ''}">
			{vital.value}
		</span>
		{#if vital.copy}
			<span
				class="flex h-5 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover/vital:opacity-100"
			>
				<CopyButton value={vital.copy} />
			</span>
		{/if}
	</span>
	<span class="flex h-4 items-center">
		{#if vital.sub}
			<span class="truncate text-xs text-muted-foreground">{vital.sub}</span>
		{/if}
	</span>
</div>
