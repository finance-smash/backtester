import { DateTime } from 'luxon';

/**
 * Utility functions for handling GMT/UTC time parsing and formatting using Luxon
 */

/**
 * Parse a time string as GMT/UTC and return Unix timestamp in seconds
 * @param timeString - Time string from CSV (assumed to be GMT)
 * @returns Unix timestamp in seconds
 */
export function parseGMTTime(timeString: string): number {
  try {
    const trimmedString = timeString.trim();
    
    // If the string already has timezone info, parse as-is
    if (trimmedString.includes('Z') || trimmedString.includes('+') || trimmedString.includes('-') || 
        trimmedString.includes('GMT') || trimmedString.includes('UTC')) {
      const dt = DateTime.fromISO(trimmedString) || DateTime.fromRFC2822(trimmedString) || DateTime.fromSQL(trimmedString);
      if (dt.isValid) {
        return Math.floor(dt.toSeconds());
      }
    }
    
    // Common formats to try, all interpreted as UTC
    const formats = [
      'yyyy-MM-dd HH:mm:ss',       // 2023-12-01 14:30:00
      'yyyy-MM-dd\'T\'HH:mm:ss',   // 2023-12-01T14:30:00
      'MM/dd/yyyy HH:mm:ss',       // 12/01/2023 14:30:00
      'dd.MM.yyyy HH:mm:ss',       // 01.12.2023 14:30:00
      'yyyy-MM-dd HH:mm',          // 2023-12-01 14:30
      'MM/dd/yyyy HH:mm',          // 12/01/2023 14:30
      'dd.MM.yyyy HH:mm',          // 01.12.2023 14:30
      'yyyy-MM-dd',                // 2023-12-01
      'MM/dd/yyyy',                // 12/01/2023
      'dd.MM.yyyy',                // 01.12.2023
    ];
    
    // Try parsing with each format, treating as UTC
    for (const format of formats) {
      const dt = DateTime.fromFormat(trimmedString, format, { zone: 'utc' });
      if (dt.isValid) {
        return Math.floor(dt.toSeconds());
      }
    }
    
    // Fallback: try automatic parsing and convert to UTC
    const autoParseAttempts = [
      () => DateTime.fromISO(trimmedString),
      () => DateTime.fromSQL(trimmedString),
      () => DateTime.fromRFC2822(trimmedString),
      () => DateTime.fromJSDate(new Date(trimmedString)).toUTC(),
    ];
    
    for (const parseAttempt of autoParseAttempts) {
      try {
        const dt = parseAttempt();
        if (dt && dt.isValid) {
          return Math.floor(dt.toUTC().toSeconds());
        }
      } catch {
        // Continue to next parse attempt
      }
    }
    
    console.warn(`Failed to parse GMT time: ${trimmedString}`);
    return NaN;
  } catch (error) {
    console.warn(`Failed to parse GMT time: ${timeString}`, error);
    return NaN;
  }
}

/**
 * Format a Unix timestamp as GMT time string
 * @param timestamp - Unix timestamp in seconds
 * @param includeSeconds - Whether to include seconds in the output
 * @returns Formatted GMT time string
 */
export function formatGMTTime(timestamp: number, includeSeconds: boolean = true): string {
  try {
    const dt = DateTime.fromSeconds(timestamp, { zone: 'utc' });
    
    if (!dt.isValid) {
      return 'Invalid Date';
    }
    
    const format = includeSeconds ? 'yyyy-MM-dd HH:mm:ss' : 'yyyy-MM-dd HH:mm';
    return dt.toFormat(format) + ' GMT';
  } catch (error) {
    console.warn(`Failed to format GMT time: ${timestamp}`, error);
    return 'Invalid Date';
  }
}

/**
 * Get current GMT time as Unix timestamp in seconds
 */
export function getCurrentGMTTime(): number {
  return Math.floor(DateTime.utc().toSeconds());
}

/**
 * Check if a time string appears to be in GMT format
 */
export function isGMTTimeString(timeString: string): boolean {
  return timeString.includes('GMT') || 
         timeString.includes('UTC') || 
         timeString.includes('Z') ||
         /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$/.test(timeString);
}

/**
 * Convert a timestamp to a readable GMT date string
 * @param timestamp - Unix timestamp in seconds
 * @returns Human-readable GMT date string
 */
export function toReadableGMTDate(timestamp: number): string {
  try {
    const dt = DateTime.fromSeconds(timestamp, { zone: 'utc' });
    
    if (!dt.isValid) {
      return 'Invalid Date';
    }
    
    return dt.toFormat('cccc, MMMM dd, yyyy \'at\' HH:mm \'GMT\'');
  } catch (error) {
    console.warn(`Failed to format readable GMT date: ${timestamp}`, error);
    return 'Invalid Date';
  }
}

/**
 * Parse multiple time formats and return the most appropriate DateTime object
 * @param timeString - Time string to parse
 * @returns Luxon DateTime object in UTC
 */
export function parseFlexibleGMTTime(timeString: string): DateTime {
  const trimmedString = timeString.trim();
  
  // Try parseGMTTime first and convert back to DateTime
  const timestamp = parseGMTTime(trimmedString);
  if (!isNaN(timestamp)) {
    return DateTime.fromSeconds(timestamp, { zone: 'utc' });
  }
  
  // Return invalid DateTime if parsing fails
  return DateTime.invalid('Unable to parse time string');
}

/**
 * Get time difference between two timestamps in human-readable format
 * @param startTimestamp - Start timestamp in seconds
 * @param endTimestamp - End timestamp in seconds
 * @returns Human-readable duration string
 */
export function getTimeDifference(startTimestamp: number, endTimestamp: number): string {
  try {
    const start = DateTime.fromSeconds(startTimestamp, { zone: 'utc' });
    const end = DateTime.fromSeconds(endTimestamp, { zone: 'utc' });
    
    if (!start.isValid || !end.isValid) {
      return 'Invalid dates';
    }
    
    const diff = end.diff(start, ['days', 'hours', 'minutes', 'seconds']).toObject();
    
    if (diff.days && diff.days > 0) {
      return `${Math.floor(diff.days)} days, ${Math.floor(diff.hours || 0)} hours`;
    } else if (diff.hours && diff.hours > 0) {
      return `${Math.floor(diff.hours)} hours, ${Math.floor(diff.minutes || 0)} minutes`;
    } else if (diff.minutes && diff.minutes > 0) {
      return `${Math.floor(diff.minutes)} minutes`;
    } else {
      return `${Math.floor(diff.seconds || 0)} seconds`;
    }
  } catch (error) {
    console.warn('Failed to calculate time difference:', error);
    return 'Unknown duration';
  }
}

/**
 * Check if a timestamp falls within trading hours (common trading sessions)
 * @param timestamp - Unix timestamp in seconds
 * @param session - Trading session ('london', 'new-york', 'tokyo', 'sydney')
 * @returns True if timestamp falls within the specified trading session
 */
export function isWithinTradingHours(timestamp: number, session: 'london' | 'new-york' | 'tokyo' | 'sydney' = 'london'): boolean {
  try {
    const dt = DateTime.fromSeconds(timestamp, { zone: 'utc' });
    
    if (!dt.isValid) {
      return false;
    }
    
    const hour = dt.hour;
    
    // Trading sessions in UTC hours (approximate)
    const sessions = {
      'london': { start: 8, end: 16 },    // 8:00 - 16:00 UTC
      'new-york': { start: 13, end: 21 }, // 13:00 - 21:00 UTC
      'tokyo': { start: 0, end: 8 },      // 0:00 - 8:00 UTC
      'sydney': { start: 22, end: 6 },    // 22:00 - 6:00 UTC (crosses midnight)
    };
    
    const { start, end } = sessions[session];
    
    if (session === 'sydney') {
      // Handle session that crosses midnight
      return hour >= start || hour < end;
    } else {
      return hour >= start && hour < end;
    }
  } catch (error) {
    console.warn('Failed to check trading hours:', error);
    return false;
  }
}