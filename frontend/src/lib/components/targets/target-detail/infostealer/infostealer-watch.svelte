<script lang="ts">
	import Zap from '@lucide/svelte/icons/zap';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import TripwireWizard, {
		type TripwireDraft
	} from '$lib/components/tripwires/tripwire-wizard.svelte';
	import { ROUTES } from '$lib/config/routes';
	import {
		ScopeKind,
		TRIPWIRE_PARAM,
		TripwireSource,
		TripwireTrigger
	} from '$lib/config/tripwires';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { tripwiresStore } from '$lib/stores/tripwires.svelte';
	import type { InfostealerWatcher } from '$lib/types/infostealer';

	interface Props {
		targetId: string;
		targetLabel: string;
		watchers: InfostealerWatcher[];
	}

	let { targetId, targetLabel, watchers }: Props = $props();

	let wizardOpen = $state(false);
	let created = $state<InfostealerWatcher[]>([]);

	let project = $derived(projectsStore.activeProject);
	let all = $derived([...watchers, ...created.filter((c) => !watchers.some((w) => w.id === c.id))]);
	let draft = $derived<TripwireDraft>({
		trigger: TripwireTrigger.Daily,
		source: TripwireSource.LeakedLogins,
		scope: { kind: ScopeKind.Targets, ids: [targetId] },
		scopeLabels: [targetLabel]
	});
</script>

{#if all.length}
	<Hint text="Checked daily by {all.map((w) => w.name).join(', ')}">
		{#snippet child(props)}
			<Button
				{...props}
				variant="outline"
				size="sm"
				href={ROUTES.tripwires({ [TRIPWIRE_PARAM]: all[0].id })}
			>
				<Zap class="size-3.5" />
				{all.length === 1 ? all[0].name : `${all.length} tripwires`}
			</Button>
		{/snippet}
	</Hint>
{:else if project}
	<Hint text="Notifies when a daily lookup adds logins">
		{#snippet child(props)}
			<Button {...props} variant="outline" size="sm" onclick={() => (wizardOpen = true)}>
				<Zap class="size-3.5" />
				Create tripwire
			</Button>
		{/snippet}
	</Hint>
{/if}

{#if project && wizardOpen}
	<TripwireWizard
		open={wizardOpen}
		projectId={project.id}
		projectSlug={project.slug}
		tripwire={null}
		{draft}
		onOpenChange={(v) => (wizardOpen = v)}
		onSaved={(t) => {
			tripwiresStore.upsert(t);
			if (t.enabled) created = [...created, { id: t.id, name: t.name }];
		}}
	/>
{/if}
