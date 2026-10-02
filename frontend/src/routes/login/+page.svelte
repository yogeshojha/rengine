<script lang="ts">
	import LoginForm from '$lib/components/auth/login-form.svelte';
	import Boxes from '@lucide/svelte/icons/boxes';
	import { pageTitle } from '$lib/utilities/page-title';
	import { PRODUCT_NAME } from '$lib/constants';
</script>

<svelte:head><title>{pageTitle('Log in')}</title></svelte:head>

<div class="flex min-h-svh flex-col items-center justify-center gap-6 bg-muted p-6 md:p-10">
	<div class="flex w-full max-w-sm flex-col gap-6">
		<a href="/" class="flex items-center gap-2 self-center font-medium text-foreground">
			<div
				class="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground"
			>
				<Boxes class="size-4" />
			</div>
			{PRODUCT_NAME}
		</a>
		<LoginForm />
	</div>
</div>
