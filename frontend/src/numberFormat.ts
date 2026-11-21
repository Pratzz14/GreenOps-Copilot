export const numberLocale = 'en-CH';
export const numberFormat = new Intl.NumberFormat(numberLocale, { maximumFractionDigits: 2 });
export const chfFormat = new Intl.NumberFormat(numberLocale, { style: 'currency', currency: 'CHF' });
export const formatCount = new Intl.NumberFormat(numberLocale, { maximumFractionDigits: 0 }).format;

export const isNumericColumn = (type: string) => /^(DECIMAL|[A-Z]*INT|DOUBLE|FLOAT)/.test(type);

const separator = numberFormat.formatToParts(1000).find(part => part.type === 'group')?.value ?? '’';

// Group stored decimal values without converting them to a floating-point number.
export function formatExactNumber(value: string | number) {
  return String(value).replace(/^[+-]?\d+(?=\.|$)/, integer =>
    integer.replace(/\B(?=(\d{3})+(?!\d))/g, separator));
}
