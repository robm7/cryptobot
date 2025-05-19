/**
 * Utility functions for exporting data
 */

/**
 * Convert an array of objects to CSV format
 * @param {Array} data - Array of objects to convert
 * @param {Array} headers - Array of header objects with 'key' and 'label' properties
 * @returns {string} CSV formatted string
 */
export function convertToCSV(data, headers) {
  if (!data || !data.length || !headers || !headers.length) {
    return '';
  }

  // Create header row
  const headerRow = headers.map(header => `"${header.label}"`).join(',');
  
  // Create data rows
  const rows = data.map(item => {
    return headers.map(header => {
      const value = item[header.key];
      // Handle different data types
      if (value === null || value === undefined) {
        return '""';
      } else if (typeof value === 'object' && value instanceof Date) {
        return `"${value.toISOString()}"`;
      } else if (typeof value === 'object') {
        return `"${JSON.stringify(value).replace(/"/g, '""')}"`;
      } else if (typeof value === 'string') {
        return `"${value.replace(/"/g, '""')}"`;
      } else {
        return `"${value}"`;
      }
    }).join(',');
  }).join('\n');

  return `${headerRow}\n${rows}`;
}

/**
 * Download data as a CSV file
 * @param {Array} data - Array of objects to export
 * @param {Array} headers - Array of header objects with 'key' and 'label' properties
 * @param {string} filename - Name of the file to download
 */
export function downloadCSV(data, headers, filename) {
  const csv = convertToCSV(data, headers);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * Format a date for display or export
 * @param {Date|string} date - Date to format
 * @param {string} format - Format string (default: 'yyyy-MM-dd HH:mm:ss')
 * @returns {string} Formatted date string
 */
export function formatDate(date, format = 'yyyy-MM-dd HH:mm:ss') {
  if (!date) return '';
  
  const d = typeof date === 'string' ? new Date(date) : date;
  
  // Simple formatter - can be replaced with a library like date-fns if needed
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const seconds = String(d.getSeconds()).padStart(2, '0');
  
  return format
    .replace('yyyy', year)
    .replace('MM', month)
    .replace('dd', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
}