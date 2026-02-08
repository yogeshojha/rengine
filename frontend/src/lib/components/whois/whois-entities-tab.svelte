<script lang="ts">
	import type { WhoisRecordRead, WhoisEntity, WhoisEntityRole } from '$lib/types/whois';
	import { ENTITY_ROLE_LABELS } from '$lib/types/whois';
	import { Badge } from '$lib/components/ui/badge';
	import * as Empty from '$lib/components/ui/empty';
	import {
		UserRound,
		Building,
		Shield,
		Wrench,
		CreditCard,
		Handshake,
		Mail,
		Phone,
		MapPin,
		Globe,
		MonitorCog,
		Cable
	} from 'lucide-svelte';

	interface Props {
		record: WhoisRecordRead;
	}

	let { record }: Props = $props();

	const ROLE_ICONS: Record<WhoisEntityRole, typeof UserRound> = {
		registrant: UserRound,
		administrative: Building,
		technical: Wrench,
		abuse: Shield,
		billing: CreditCard,
		registrar: Handshake,
		sponsor: Globe,
		noc: MonitorCog,
		routing: Cable
	};

	const ROLE_ORDER: WhoisEntityRole[] = [
		'registrant',
		'technical',
		'administrative',
		'abuse',
		'registrar',
		'billing',
		'sponsor',
		'noc',
		'routing'
	];

	let populatedRoles = $derived.by(() => {
		if (!record.parsed_data?.entities) return [];
		return ROLE_ORDER.filter((role) => {
			const entities = record.parsed_data?.entities[role];
			return entities && entities.length > 0;
		});
	});

	function formatAddress(entity: WhoisEntity): string | null {
		if (!entity.address) return null;
		const parts = [
			entity.address.street_address,
			[entity.address.locality, entity.address.region, entity.address.postal_code]
				.filter(Boolean)
				.join(', '),
			entity.address.country
		].filter(Boolean);
		return parts.length > 0 ? parts.join('\n') : null;
	}

	function getEntities(role: WhoisEntityRole): WhoisEntity[] {
		return record.parsed_data?.entities[role] ?? [];
	}
</script>

{#if populatedRoles.length === 0}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<UserRound />
			</Empty.Media>
			<Empty.Title>No entity data available</Empty.Title>
			<Empty.Description>
				WHOIS privacy protection may be hiding contact details for this record.
			</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else}
	<div class="space-y-4 py-1">
		{#each populatedRoles as role}
			{#each getEntities(role) as entity}
				{#if entity.name || entity.email || entity.tel || entity.handle || formatAddress(entity)}
					{@const RoleIcon = ROLE_ICONS[role]}
					<div class="rounded-lg border border-border/60 bg-card">
						<div
							class="flex items-center gap-2 px-4 py-2.5 border-b border-border/40 bg-muted/30 rounded-t-lg"
						>
							<RoleIcon class="h-4 w-4 text-muted-foreground" />
							<span class="text-sm font-medium">{ENTITY_ROLE_LABELS[role]}</span>
							{#if entity.handle}
								<Badge variant="outline" class="text-[10px] font-mono ml-auto">
									{entity.handle}
								</Badge>
							{/if}
						</div>

						<div class="px-4 py-3 space-y-2.5">
							{#if entity.name}
								<div class="flex items-start gap-2.5">
									<UserRound class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
									<p class="text-sm">{entity.name}</p>
								</div>
							{/if}

							{#if entity.email}
								<div class="flex items-start gap-2.5">
									<Mail class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
									<a href="mailto:{entity.email}" class="text-sm text-primary hover:underline">
										{entity.email}
									</a>
								</div>
							{/if}

							{#if entity.tel}
								<div class="flex items-start gap-2.5">
									<Phone class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
									<p class="text-sm font-mono">{entity.tel}</p>
								</div>
							{/if}

							{#if formatAddress(entity)}
								<div class="flex items-start gap-2.5">
									<MapPin class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
									<p class="text-sm whitespace-pre-line text-muted-foreground">
										{formatAddress(entity)}
									</p>
								</div>
							{/if}

							{#if entity.whois_server}
								<div class="flex items-start gap-2.5">
									<Globe class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
									<p class="text-sm font-mono text-muted-foreground">{entity.whois_server}</p>
								</div>
							{/if}
						</div>
					</div>
				{/if}
			{/each}
		{/each}
	</div>
{/if}
