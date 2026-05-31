import { TaskStatus } from '$lib/types/task-status';

export interface TaskStatusConfig {
	label: string;
	dotClass: string;
	textClass: string;
	borderClass: string;
}

export const TASK_STATUS_CONFIG: Record<TaskStatus, TaskStatusConfig> = {
	[TaskStatus.SUCCESS]: {
		label: 'Completed',
		dotClass: 'bg-green-500',
		textClass: 'text-green-600 dark:text-green-400',
		borderClass: 'border-green-500/20'
	},
	[TaskStatus.QUERYING]: {
		label: 'Running',
		dotClass: 'bg-blue-500 animate-pulse',
		textClass: 'text-blue-600 dark:text-blue-400',
		borderClass: 'border-blue-500/20'
	},
	[TaskStatus.PENDING]: {
		label: 'Queued',
		dotClass: 'bg-yellow-500',
		textClass: 'text-yellow-600 dark:text-yellow-400',
		borderClass: 'border-yellow-500/20'
	},
	[TaskStatus.FAILED]: {
		label: 'Failed',
		dotClass: 'bg-red-500',
		textClass: 'text-red-600 dark:text-red-400',
		borderClass: 'border-red-500/20'
	},
	[TaskStatus.SKIPPED]: {
		label: 'Skipped',
		dotClass: 'bg-zinc-400 dark:bg-zinc-600',
		textClass: 'text-muted-foreground',
		borderClass: 'border-zinc-500/20'
	}
};

export function getTaskStatusConfig(status: TaskStatus): TaskStatusConfig {
	return TASK_STATUS_CONFIG[status];
}
