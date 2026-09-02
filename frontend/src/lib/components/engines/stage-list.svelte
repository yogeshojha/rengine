<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import Minus from '@lucide/svelte/icons/minus';
	import Ban from '@lucide/svelte/icons/ban';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { cn } from '$lib/utils';
	import { phaseLabel, type StageCatalogEntry, type StageConfig } from '$lib/types/scan-engine';

	type StageState = 'on' | 'off' | 'blocked';

	interface Props {
		stages: StageCatalogEntry[];
		config: Record<string, StageConfig>;
		intensity?: string;
		variant?: 'matrix' | 'inline';
		max?: number;
		class?: string;
	}

	let {
		stages,
		config,
		intensity = 'normal',
		variant = 'matrix',
		max = 5,
		class: className
	}: Props = $props();

	function stateOf(stage: StageCatalogEntry): StageState {
		const enabled = Boolean(config?.[stage.name]?.enabled ?? stage.defaults.enabled);
		if (!enabled) return 'off';
		if (intensity === 'passive' && stage.touches_target) return 'blocked';
		return 'on';
	}

	const phases = $derived([...new Set(stages.map((s) => s.phase))]);
	const running = $derived(stages.filter((s) => stateOf(s) === 'on'));
	const off = $derived(stages.filter((s) => stateOf(s) !== 'on'));

	const inline = $derived.by(() => {
		if (!stages.length) return '';
		if (!running.length) return 'No stages enabled.';
		if (!off.length) return `All ${stages.length} stages.`;
		if (off.length <= 3 && off.length < running.length) {
			return `All except ${off.map((s) => s.title).join(', ')}.`;
		}
		const shown = running.slice(0, max).map((s) => s.title);
		const rest = running.length - shown.length;
		return `${shown.join(', ')}${rest ? ` +${rest} more` : ''}`;
	});
</script>

{#if variant === 'inline'}
	<p class={cn('text-xs leading-relaxed text-foreground', className)}>{inline}</p>
{:else}
	<div class={cn('flex flex-col gap-2.5', className)}>
		{#each phases as phase (phase)}
			{@const list = stages.filter((s) => s.phase === phase)}
			{@const on = list.filter((s) => stateOf(s) === 'on').length}
			<div>
				<div
					class="mb-1 flex items-baseline justify-between gap-2 text-[10px] tracking-wider text-muted-foreground uppercase"
				>
					<span>{phaseLabel(phase)}</span>
					<span class="tracking-normal tabular-nums normal-case">{on}/{list.length}</span>
				</div>
				<ul class="grid grid-cols-2 gap-x-3 gap-y-1">
					{#each list as stage (stage.name)}
						{@const state = stateOf(stage)}
						<li
							class={cn(
								'flex min-w-0 items-center gap-1.5 text-xs',
								state === 'on' ? 'text-foreground' : 'text-muted-foreground/70'
							)}
						>
							{#if state === 'on'}
								<Check size={12} class="shrink-0 text-primary" aria-label="On" />
							{:else if state === 'blocked'}
								<Tooltip.Root>
									<Tooltip.Trigger>
										{#snippet child({ props })}
											<span {...props} class="inline-flex shrink-0">
												<Ban
													size={11}
													class="text-warning"
													aria-label="Skipped at passive intensity"
												/>
											</span>
										{/snippet}
									</Tooltip.Trigger>
									<Tooltip.Content class="text-xs">Skipped at passive intensity</Tooltip.Content>
								</Tooltip.Root>
							{:else}
								<Minus size={12} class="shrink-0 opacity-60" aria-label="Off" />
							{/if}
							<span class="truncate">{stage.title}</span>
						</li>
					{/each}
				</ul>
			</div>
		{/each}
	</div>
{/if}
