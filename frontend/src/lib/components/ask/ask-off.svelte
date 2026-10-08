<script lang="ts">
	import Ban from '@lucide/svelte/icons/ban';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import PowerOff from '@lucide/svelte/icons/power-off';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button';
	import { AskOffCode } from '$lib/config/ask';
	import { ROUTES } from '$lib/config/routes';

	interface Props {
		reason: string;
		code?: string | null;
		admin?: boolean;
		/** Set when the AI status did not load: the card offers Retry instead of setup. */
		onRetry?: () => void;
		detail?: string | null;
	}

	let { reason, code = null, admin = false, onRetry, detail = null }: Props = $props();

	let Icon = $derived(
		onRetry
			? TriangleAlert
			: code === AskOffCode.NO_KEY
				? KeyRound
				: code === AskOffCode.FEATURE_OFF
					? Ban
					: PowerOff
	);
</script>

<div class="flex w-full items-center gap-4 rounded-2xl border bg-card px-5 py-4 shadow-sm">
	<span
		class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground"
	>
		<Icon class="size-5" />
	</span>
	<div class="flex min-w-0 flex-1 flex-col gap-0.5">
		<span class="text-sm font-medium">{reason}</span>
		{#if onRetry}
			{#if detail}
				<span class="text-xs text-muted-foreground">{detail}</span>
			{/if}
		{:else if !admin}
			<span class="text-xs text-muted-foreground">An administrator sets up AI in Settings.</span>
		{/if}
	</div>
	{#if onRetry}
		<Button variant="outline" size="sm" class="shrink-0" onclick={onRetry}>Retry</Button>
	{:else if admin}
		<Button href={ROUTES.ai('connection')} size="sm" class="shrink-0">Set up AI</Button>
	{/if}
</div>
