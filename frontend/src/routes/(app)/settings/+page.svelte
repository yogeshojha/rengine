<script lang="ts">
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import ApiKeysTab from '$lib/components/settings/api-keys-tab.svelte';
	import KeyIcon from '@lucide/svelte/icons/key-round';
	import SlidersHorizontalIcon from '@lucide/svelte/icons/sliders-horizontal';
</script>

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">Settings</h1>
		<p class="text-sm text-muted-foreground mt-1">
			Manage your reNgine instance configuration
		</p>
	</div>

	<Tabs.Root value="api-keys">
		<Tabs.List>
			<Tabs.Trigger value="api-keys" class="gap-1.5">
				<KeyIcon class="size-4" />
				API Keys
			</Tabs.Trigger>
			<Tabs.Trigger value="general" class="gap-1.5">
				<SlidersHorizontalIcon class="size-4" />
				General
			</Tabs.Trigger>
		</Tabs.List>

		<Tabs.Content value="api-keys" class="mt-6">
			<ApiKeysTab />
		</Tabs.Content>

		<Tabs.Content value="general" class="mt-6">
			<Card.Root>
				<Card.Content class="flex items-center justify-center py-16">
					<div class="text-center space-y-2">
						<SlidersHorizontalIcon class="size-10 text-muted-foreground/40 mx-auto" />
						<!-- TODO: General settings -->
					</div>
				</Card.Content>
			</Card.Root>
		</Tabs.Content>
	</Tabs.Root>
</div>
