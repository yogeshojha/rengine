// mirrors shared/services/asset_export/writer.py:cell
const FORMULA_LEAD = /^[=+\-@\t\r]/;

export function csvCell(value: string): string {
	const text = FORMULA_LEAD.test(value) ? `'${value}` : value;
	return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}
