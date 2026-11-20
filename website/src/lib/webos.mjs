/** @param {string | null} version */
export function webosCategory(version) {
  const match = version?.match(/^(?:SDK\s*)?(\d+)(?:\.(\d+))?(?=[\s.;/-]|$)/i);
  if (!match) return 'unknown';
  const major = Number(match[1]);
  if ((major === 4 && Number(match[2]) >= 5) || major === 5) return '4.5-5';
  if (major >= 7 && major <= 11) return String(major + 15);
  if ((major >= 1 && major <= 6) || (major >= 22 && major <= 26))
    return String(major);
  return 'unknown';
}
