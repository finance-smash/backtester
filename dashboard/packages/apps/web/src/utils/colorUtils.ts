/**
 * Utility functions for generating and managing colors for indicators
 */

/**
 * Generate a distinct color for indicators using HSL color space
 * @param index - Index of the indicator (used for consistent color assignment)
 * @param total - Total number of indicators (used to distribute colors evenly)
 * @returns RGB color string
 */
export function generateIndicatorColor(index: number, total: number): string {
  // Use golden ratio to distribute hues evenly and avoid similar colors
  const goldenRatio = 0.618033988749895;
  const hue = (index * goldenRatio * 360) % 360;
  
  // Use higher saturation and lightness for better visibility on dark chart background
  const saturation = 70 + (index % 3) * 10; // 70%, 80%, 90%
  const lightness = 55 + (index % 2) * 10;   // 55%, 65%
  
  return hslToRgb(hue, saturation, lightness);
}

/**
 * Convert HSL to RGB color string
 * @param h - Hue (0-360)
 * @param s - Saturation (0-100)
 * @param l - Lightness (0-100)
 * @returns RGB color string in format "rgb(r, g, b)"
 */
function hslToRgb(h: number, s: number, l: number): string {
  h = h / 360;
  s = s / 100;
  l = l / 100;

  const hue2rgb = (p: number, q: number, t: number): number => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1/6) return p + (q - p) * 6 * t;
    if (t < 1/2) return q;
    if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
    return p;
  };

  let r: number, g: number, b: number;

  if (s === 0) {
    r = g = b = l; // achromatic
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }

  const toInt = (val: number) => Math.round(val * 255);
  return `rgb(${toInt(r)}, ${toInt(g)}, ${toInt(b)})`;
}

/**
 * Pre-defined color palette for indicators (fallback if needed)
 */
export const INDICATOR_COLORS = [
  '#ff6b6b', // Red
  '#4ecdc4', // Teal
  '#45b7d1', // Blue
  '#96ceb4', // Green
  '#feca57', // Yellow
  '#ff9ff3', // Pink
  '#54a0ff', // Light Blue
  '#5f27cd', // Purple
  '#00d2d3', // Cyan
  '#ff9f43', // Orange
  '#0abde3', // Sky Blue
  '#fda085', // Peach
  '#fd79a8', // Rose
  '#6c5ce7', // Lavender
  '#00b894', // Emerald
];

/**
 * Get a color from the predefined palette
 * @param index - Index of the indicator
 * @returns RGB color string
 */
export function getPreDefinedColor(index: number): string {
  return INDICATOR_COLORS[index % INDICATOR_COLORS.length];
}

/**
 * Generate distinct colors for a list of indicator names
 * @param indicatorNames - Array of indicator names
 * @returns Map of indicator name to color
 */
export function generateIndicatorColorMap(indicatorNames: string[]): Map<string, string> {
  const colorMap = new Map<string, string>();
  
  indicatorNames.forEach((name, index) => {
    const color = generateIndicatorColor(index, indicatorNames.length);
    colorMap.set(name, color);
  });
  
  return colorMap;
}
