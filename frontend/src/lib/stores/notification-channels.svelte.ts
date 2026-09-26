import { notificationChannelsApi } from '$lib/api/notification-channels';
import { createCrudStore } from '$lib/stores/crud.svelte';

export const notificationChannelsStore = createCrudStore(notificationChannelsApi, {
	notLoaded: 'Notification channels not loaded',
	notCreated: 'Notification channel not created',
	notSaved: 'Notification channel not saved',
	notDeleted: 'Notification channel not deleted',
	testFailed: 'Notification channel test failed'
});
