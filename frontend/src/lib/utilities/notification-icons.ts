import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
import CircleCheck from '@lucide/svelte/icons/circle-check';
import Info from '@lucide/svelte/icons/info';
import Scan from '@lucide/svelte/icons/scan';
import Server from '@lucide/svelte/icons/server';
import Shield from '@lucide/svelte/icons/shield';
import Bug from '@lucide/svelte/icons/bug';
import Target from '@lucide/svelte/icons/target';
import HardDrive from '@lucide/svelte/icons/hard-drive';
import Plug from '@lucide/svelte/icons/plug';
import type { MessageLevel } from '$lib/types/message-level';
import {
	NOTIFICATION_TYPES,
	type NotificationType,
	type NotificationSeverity
} from '$lib/types/notification';
import type { IconComponent } from '$lib/config/icons';

interface SeverityIcon {
	icon: IconComponent;
	class: string;
}

const SEVERITY_ICONS: Record<MessageLevel, SeverityIcon> = {
	error: { icon: ShieldAlert, class: 'text-destructive' },
	warning: { icon: TriangleAlert, class: 'text-warning' },
	success: { icon: CircleCheck, class: 'text-foreground' },
	info: { icon: Info, class: 'text-chart-1' }
};

const TYPE_ICONS: Record<NotificationType, IconComponent> = {
	scan: Scan,
	system: Server,
	security: Shield,
	vulnerability: Bug,
	target: Target,
	resource: HardDrive,
	integration: Plug
};

export const getSeverityIcon = (severity: NotificationSeverity): SeverityIcon =>
	SEVERITY_ICONS[severity] ?? SEVERITY_ICONS.info;

export const getTypeIcon = (type: NotificationType): IconComponent => TYPE_ICONS[type];

export const emptyTypeCounts = (): Record<NotificationType | 'all', number> => {
	const counts = { all: 0 } as Record<NotificationType | 'all', number>;
	for (const type of NOTIFICATION_TYPES) counts[type] = 0;
	return counts;
};
