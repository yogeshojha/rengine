<script lang="ts">
	import { CHAT_GROUP_LABELS, CHAT_GROUP_ORDER } from '$lib/config/channels';
	import type { ChannelCommand } from '$lib/types/remote-control';

	interface Props {
		commands: ChannelCommand[];
	}

	let { commands }: Props = $props();

	const LABEL = 'text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase';

	const groups = $derived(
		CHAT_GROUP_ORDER.map((group) => ({
			group,
			label: CHAT_GROUP_LABELS[group],
			rows: commands.filter((c) => c.group === group)
		})).filter((g) => g.rows.length)
	);

	const short = (usage: string) => usage.split(' [')[0];
</script>

<div class="grid gap-x-8 gap-y-5 px-4 py-5 sm:grid-cols-2 xl:grid-cols-3">
	{#each groups as group (group.group)}
		<div class="min-w-0">
			<h4 class="mb-1.5 {LABEL}">{group.label}</h4>
			<ul class="flex flex-col">
				{#each group.rows as command (command.name)}
					<li class="flex items-baseline gap-2 py-1 leading-5">
						<code class="shrink-0 font-mono text-xs">{short(command.usage)}</code>
						<span class="min-w-0 text-xs text-muted-foreground">{command.title}</span>
						{#if command.capability !== 'read'}
							<span
								class="shrink-0 text-2xs {command.touches_target
									? 'text-warning'
									: 'text-muted-foreground'}"
							>
								confirm
							</span>
						{/if}
					</li>
				{/each}
			</ul>
		</div>
	{/each}
</div>
