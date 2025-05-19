import React, { useState, useEffect, useRef } from 'react';

/**
 * FeatureHighlight component highlights a specific feature or element
 * in the application with a spotlight effect and description.
 * 
 * @param {Object} props - Component props
 * @param {string} props.targetId - ID of the element to highlight
 * @param {string} props.title - Title of the highlighted feature
 * @param {string} props.description - Description of the highlighted feature
 * @param {string} props.position - Position of the description (top, right, bottom, left)
 * @param {function} props.onDismiss - Callback when the highlight is dismissed
 * @param {function} props.onNext - Callback when the user clicks next
 * @param {boolean} props.isLast - Whether this is the last highlight in a sequence
 */
export default function FeatureHighlight({
  targetId,
  title,
  description,
  position = 'bottom',
  onDismiss,
  onNext,
  isLast = false
}) {
  const [targetElement, setTargetElement] = useState(null);
  const [targetRect, setTargetRect] = useState(null);
  const [windowSize, setWindowSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0
  });
  const highlightRef = useRef(null);
  
  // Find the target element and calculate its position
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const element = document.getElementById(targetId);
      if (element) {
        setTargetElement(element);
        updateTargetRect(element);
      }
      
      const handleResize = () => {
        setWindowSize({
          width: window.innerWidth,
          height: window.innerHeight
        });
        if (element) {
          updateTargetRect(element);
        }
      };
      
      window.addEventListener('resize', handleResize);
      return () => {
        window.removeEventListener('resize', handleResize);
      };
    }
  }, [targetId]);
  
  // Update target rect when window size changes
  useEffect(() => {
    if (targetElement) {
      updateTargetRect(targetElement);
    }
  }, [windowSize, targetElement]);
  
  // Scroll target into view if needed
  useEffect(() => {
    if (targetElement) {
      const rect = targetElement.getBoundingClientRect();
      const isInViewport = 
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= window.innerHeight &&
        rect.right <= window.innerWidth;
      
      if (!isInViewport) {
        targetElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
      }
    }
  }, [targetElement]);
  
  const updateTargetRect = (element) => {
    const rect = element.getBoundingClientRect();
    setTargetRect({
      top: rect.top,
      left: rect.left,
      width: rect.width,
      height: rect.height,
      bottom: rect.bottom,
      right: rect.right
    });
  };
  
  // If no target element is found, don't render anything
  if (!targetElement || !targetRect) {
    return null;
  }
  
  // Calculate position for the description box
  let descriptionStyle = {};
  switch (position) {
    case 'top':
      descriptionStyle = {
        bottom: window.innerHeight - targetRect.top + 10,
        left: targetRect.left + (targetRect.width / 2) - 150
      };
      break;
    case 'right':
      descriptionStyle = {
        left: targetRect.right + 10,
        top: targetRect.top + (targetRect.height / 2) - 75
      };
      break;
    case 'bottom':
      descriptionStyle = {
        top: targetRect.bottom + 10,
        left: targetRect.left + (targetRect.width / 2) - 150
      };
      break;
    case 'left':
      descriptionStyle = {
        right: window.innerWidth - targetRect.left + 10,
        top: targetRect.top + (targetRect.height / 2) - 75
      };
      break;
    default:
      descriptionStyle = {
        top: targetRect.bottom + 10,
        left: targetRect.left + (targetRect.width / 2) - 150
      };
  }
  
  // Ensure the description box stays within viewport
  if (descriptionStyle.left < 10) descriptionStyle.left = 10;
  if (descriptionStyle.right < 10) descriptionStyle.right = 10;
  if (descriptionStyle.top < 10) descriptionStyle.top = 10;
  if (descriptionStyle.bottom < 10) descriptionStyle.bottom = 10;
  
  if (descriptionStyle.left + 300 > window.innerWidth) {
    descriptionStyle.left = window.innerWidth - 310;
  }
  
  if (descriptionStyle.top + 150 > window.innerHeight) {
    descriptionStyle.top = window.innerHeight - 160;
  }
  
  return (
    <div className="fixed inset-0 z-50 pointer-events-none">
      {/* Overlay with cutout for the target element */}
      <div className="absolute inset-0 bg-black bg-opacity-50">
        <svg width="100%" height="100%">
          <defs>
            <mask id="spotlight">
              <rect width="100%" height="100%" fill="white" />
              <rect
                x={targetRect.left - 5}
                y={targetRect.top - 5}
                width={targetRect.width + 10}
                height={targetRect.height + 10}
                fill="black"
                rx="4"
                ry="4"
              />
            </mask>
          </defs>
          <rect
            width="100%"
            height="100%"
            fill="black"
            mask="url(#spotlight)"
          />
        </svg>
      </div>
      
      {/* Highlight border around target */}
      <div
        className="absolute border-2 border-blue-500 rounded-md pointer-events-none"
        style={{
          top: targetRect.top - 5,
          left: targetRect.left - 5,
          width: targetRect.width + 10,
          height: targetRect.height + 10,
          boxShadow: '0 0 0 2px rgba(59, 130, 246, 0.5)'
        }}
      ></div>
      
      {/* Description box */}
      <div
        ref={highlightRef}
        className="absolute bg-white rounded-lg shadow-lg p-4 w-72 pointer-events-auto"
        style={descriptionStyle}
      >
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-semibold text-lg text-gray-900">{title}</h3>
          <button
            onClick={onDismiss}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <p className="text-gray-600 mb-4">{description}</p>
        <div className="flex justify-between">
          <button
            onClick={onDismiss}
            className="text-gray-600 hover:text-gray-800 text-sm"
          >
            Skip all
          </button>
          <button
            onClick={onNext}
            className="bg-blue-600 text-white px-4 py-1 rounded hover:bg-blue-700 text-sm"
          >
            {isLast ? 'Finish' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * FeatureHighlightTour component shows a sequence of feature highlights
 * 
 * @param {Object} props - Component props
 * @param {Array} props.highlights - Array of highlight objects
 * @param {function} props.onComplete - Callback when the tour is completed
 * @param {string} props.tourId - Unique identifier for this tour
 */
export function FeatureHighlightTour({ highlights, onComplete, tourId }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isDismissed, setIsDismissed] = useState(false);
  
  useEffect(() => {
    // Check if this tour has been completed before
    const completedTours = JSON.parse(localStorage.getItem('cryptobot_completed_tours') || '[]');
    if (completedTours.includes(tourId)) {
      setIsDismissed(true);
    }
  }, [tourId]);
  
  const handleNext = () => {
    if (currentIndex < highlights.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      handleComplete();
    }
  };
  
  const handleDismiss = () => {
    handleComplete();
  };
  
  const handleComplete = () => {
    setIsDismissed(true);
    
    // Mark this tour as completed
    const completedTours = JSON.parse(localStorage.getItem('cryptobot_completed_tours') || '[]');
    if (!completedTours.includes(tourId)) {
      completedTours.push(tourId);
      localStorage.setItem('cryptobot_completed_tours', JSON.stringify(completedTours));
    }
    
    if (onComplete) {
      onComplete();
    }
  };
  
  if (isDismissed || highlights.length === 0) {
    return null;
  }
  
  const currentHighlight = highlights[currentIndex];
  
  return (
    <FeatureHighlight
      targetId={currentHighlight.targetId}
      title={currentHighlight.title}
      description={currentHighlight.description}
      position={currentHighlight.position}
      onDismiss={handleDismiss}
      onNext={handleNext}
      isLast={currentIndex === highlights.length - 1}
    />
  );
}

/**
 * Reset all completed tours
 */
export function resetCompletedTours() {
  localStorage.removeItem('cryptobot_completed_tours');
}

/**
 * Check if a specific tour has been completed
 * @param {string} tourId - Tour ID
 * @returns {boolean} True if the tour has been completed
 */
export function isTourCompleted(tourId) {
  const completedTours = JSON.parse(localStorage.getItem('cryptobot_completed_tours') || '[]');
  return completedTours.includes(tourId);
}