import Scan from '@lucide/svelte/icons/scan';
import Server from '@lucide/svelte/icons/server';
import Shield from '@lucide/svelte/icons/shield';
import Bug from '@lucide/svelte/icons/bug';
import Target from '@lucide/svelte/icons/target';
import HardDrive from '@lucide/svelte/icons/hard-drive';
import Plug from '@lucide/svelte/icons/plug';
import { NOTIFICATION_TYPES, type NotificationType } from '$lib/types/notification';
import type { IconComponent } from '$lib/config/icons';

const TYPE_ICONS: Record<NotificationType, IconComponent> = {
	scan: Scan,
	system: Server,
	security: Shield,
	vulnerability: Bug,
	target: Target,
	resource: HardDrive,
	integration: Plug
};

export const getTypeIcon = (type: NotificationType): IconComponent => TYPE_ICONS[type];

export const emptyTypeCounts = (): Record<NotificationType | 'all', number> => {
	const counts = { all: 0 } as Record<NotificationType | 'all', number>;
	for (const type of NOTIFICATION_TYPES) counts[type] = 0;
	return counts;
};
