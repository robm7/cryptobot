import React from 'react';

export default function FormField({ 
  label, 
  tooltip, 
  children, 
  helpText 
}) {
  return (
    <div className="mb-4"> {/* Added consistent bottom margin */}
      <label className="block text-sm font-semibold text-gray-800 mb-1.5 flex items-center"> {/* Increased font weight, changed color, increased bottom margin, added flex for alignment */}
        {label}
        {tooltip && (
          <span
            className="ml-1.5 text-gray-400 hover:text-gray-600 cursor-help" // Adjusted margin
            title={tooltip} // Keeping title for basic tooltip, can be enhanced with HelpTooltip component later if needed
          >
            <svg
              className="inline-block w-4 h-4" // Kept size
              fill="currentColor" // Changed to fill for better visibility
              viewBox="0 0 20 20" // Adjusted viewBox for a potentially more standard icon
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </span>
        )}
      </label>
      <div className="mt-1"> {/* Added a div wrapper for children to control spacing if needed */}
        {children}
      </div>
      {helpText && <p className="mt-1.5 text-xs text-gray-500">{helpText}</p>} {/* Adjusted top margin */}
    </div>
  );
}