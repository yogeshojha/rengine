export interface RetentionOption {
	value: string;
	label: string;
}

// mirrors shared/definitions/retention.py:KEEP_FOREVER
export const KEEP_FOREVER = '0';

// mirrors shared/definitions/retention.py:SCAN_RETENTION_DAYS
export const SCAN_RETENTION: RetentionOption[] = [
	{ value: '30', label: '30 days' },
	{ value: '60', label: '60 days' },
	{ value: '90', label: '90 days' },
	{ value: '180', label: '180 days' },
	{ value: '365', label: '1 year' },
	{ value: KEEP_FOREVER, label: 'Keep forever' }
];

// mirrors shared/definitions/retention.py:SCREENSHOT_RETENTION_DAYS
export const SCREENSHOT_RETENTION: RetentionOption[] = [
	{ value: '7', label: '7 days' },
	{ value: '14', label: '14 days' },
	{ value: '30', label: '30 days' },
	{ value: '60', label: '60 days' },
	{ value: '90', label: '90 days' },
	{ value: KEEP_FOREVER, label: 'Keep forever' }
];

export function retentionLabel(options: RetentionOption[], value: string): string {
	return options.find((o) => o.value === value)?.label ?? `${value} days`;
}
