import React, { useState } from 'react';
import { getSetupPreferences } from '../utils/firstRunUtils';

/**
 * HelpTooltip component displays a tooltip with helpful information
 * about a specific feature or element in the application.
 * 
 * @param {Object} props - Component props
 * @param {string} props.id - Unique identifier for the tooltip
 * @param {string} props.content - The content to display in the tooltip
 * @param {string} props.position - Position of the tooltip (top, right, bottom, left)
 * @param {boolean} props.forceShow - Force the tooltip to be shown regardless of user preferences
 * @param {React.ReactNode} props.children - The element that triggers the tooltip
 */
export default function HelpTooltip({ 
  id, 
  content, 
  position = 'top', 
  forceShow = false,
  children 
}) {
  const [isVisible, setIsVisible] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  
  // Check if tooltips are enabled in user preferences
  const preferences = getSetupPreferences();
  const tooltipsEnabled = preferences?.showTooltips !== false;
  
  // If tooltips are disabled and not forced, don't render anything
  if (!tooltipsEnabled && !forceShow) {
    return children;
  }
  
  // If this specific tooltip has been dismissed, don't show it
  if (isDismissed && !forceShow) {
    return children;
  }
  
  const handleDismiss = (e) => {
    e.stopPropagation();
    setIsDismissed(true);
    
    // Store dismissed tooltips in localStorage
    const dismissedTooltips = JSON.parse(localStorage.getItem('cryptobot_dismissed_tooltips') || '[]');
    if (!dismissedTooltips.includes(id)) {
      dismissedTooltips.push(id);
      localStorage.setItem('cryptobot_dismissed_tooltips', JSON.stringify(dismissedTooltips));
    }
  };
  
  // Determine tooltip position classes
  let positionClasses = '';
  switch (position) {
    case 'top':
      positionClasses = 'bottom-full left-1/2 transform -translate-x-1/2 mb-2';
      break;
    case 'right':
      positionClasses = 'left-full top-1/2 transform -translate-y-1/2 ml-2';
      break;
    case 'bottom':
      positionClasses = 'top-full left-1/2 transform -translate-x-1/2 mt-2';
      break;
    case 'left':
      positionClasses = 'right-full top-1/2 transform -translate-y-1/2 mr-2';
      break;
    default:
      positionClasses = 'bottom-full left-1/2 transform -translate-x-1/2 mb-2';
  }
  
  // Determine arrow position classes
  let arrowClasses = '';
  switch (position) {
    case 'top':
      arrowClasses = 'top-full left-1/2 transform -translate-x-1/2 border-t-gray-800 border-l-transparent border-r-transparent border-b-transparent';
      break;
    case 'right':
      arrowClasses = 'right-full top-1/2 transform -translate-y-1/2 border-r-gray-800 border-t-transparent border-b-transparent border-l-transparent';
      break;
    case 'bottom':
      arrowClasses = 'bottom-full left-1/2 transform -translate-x-1/2 border-b-gray-800 border-l-transparent border-r-transparent border-t-transparent';
      break;
    case 'left':
      arrowClasses = 'left-full top-1/2 transform -translate-y-1/2 border-l-gray-800 border-t-transparent border-b-transparent border-r-transparent';
      break;
    default:
      arrowClasses = 'top-full left-1/2 transform -translate-x-1/2 border-t-gray-800 border-l-transparent border-r-transparent border-b-transparent';
  }
  
  return (
    <div 
      className="relative inline-block"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      
      {isVisible && (
        <div 
          className={`absolute z-50 w-64 p-3 bg-gray-800 text-white text-sm rounded shadow-lg ${positionClasses}`}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex justify-between items-start mb-1">
            <div className="font-semibold">Help</div>
            <button 
              onClick={handleDismiss}
              className="text-gray-400 hover:text-white"
              aria-label="Dismiss"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div>{content}</div>
          <div 
            className={`absolute w-0 h-0 border-4 ${arrowClasses}`}
          ></div>
        </div>
      )}
    </div>
  );
}

/**
 * Reset all dismissed tooltips
 */
export function resetDismissedTooltips() {
  localStorage.removeItem('cryptobot_dismissed_tooltips');
}

/**
 * Check if a specific tooltip has been dismissed
 * @param {string} id - Tooltip ID
 * @returns {boolean} True if the tooltip has been dismissed
 */
export function isTooltipDismissed(id) {
  const dismissedTooltips = JSON.parse(localStorage.getItem('cryptobot_dismissed_tooltips') || '[]');
  return dismissedTooltips.includes(id);
}

/**
 * Reset all dismissed tooltips
 */
export function resetDismissedTooltips() {
  localStorage.removeItem('cryptobot_dismissed_tooltips');
}