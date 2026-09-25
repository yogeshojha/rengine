// mirrors shared/definitions/scan_admission.py
export const AUTOMATIC = 0;
export const MAX_CONCURRENT_SCANS = 50;

export const CONCURRENT_SCAN_CHOICES = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 30, 40, 50];

export function queueLabel(ahead: number): string {
	return ahead === 0 ? 'Next' : `${ahead} ahead`;
}
