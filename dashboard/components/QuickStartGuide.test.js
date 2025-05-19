/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuickStartGuide from './QuickStartGuide';

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: jest.fn(key => store[key] || null),
    setItem: jest.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn(key => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    })
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

describe('QuickStartGuide', () => {
  beforeEach(() => {
    localStorageMock.clear();
    jest.clearAllMocks();
  });

  it('renders the first step of the guide', () => {
    render(<QuickStartGuide />);
    
    expect(screen.getByText('Quick Start Guide')).toBeInTheDocument();
    expect(screen.getByText('Dashboard Overview')).toBeInTheDocument();
    expect(screen.getByText('Step 1 of 5')).toBeInTheDocument();
  });

  it('navigates to the next step when Next button is clicked', () => {
    render(<QuickStartGuide />);
    
    // Initial step is Dashboard Overview
    expect(screen.getByText('Dashboard Overview')).toBeInTheDocument();
    
    // Click Next button
    fireEvent.click(screen.getByText('Next'));
    
    // Should now be on Creating a Strategy step
    expect(screen.getByText('Creating a Strategy')).toBeInTheDocument();
    expect(screen.getByText('Step 2 of 5')).toBeInTheDocument();
  });

  it('navigates to the previous step when Previous button is clicked', () => {
    render(<QuickStartGuide />);
    
    // Navigate to second step
    fireEvent.click(screen.getByText('Next'));
    expect(screen.getByText('Creating a Strategy')).toBeInTheDocument();
    
    // Navigate back to first step
    fireEvent.click(screen.getByText('Previous'));
    expect(screen.getByText('Dashboard Overview')).toBeInTheDocument();
  });

  it('disables the Previous button on the first step', () => {
    render(<QuickStartGuide />);
    
    // Previous button should be disabled on first step
    const previousButton = screen.getByText('Previous');
    expect(previousButton).toBeDisabled();
    expect(previousButton).toHaveClass('cursor-not-allowed');
  });

  it('shows Finish button on the last step', () => {
    render(<QuickStartGuide />);
    
    // Navigate to the last step
    for (let i = 0; i < 4; i++) {
      fireEvent.click(screen.getByText('Next'));
    }
    
    // Should now be on the last step
    expect(screen.getByText('Monitoring Performance')).toBeInTheDocument();
    expect(screen.getByText('Step 5 of 5')).toBeInTheDocument();
    
    // Should show Finish button instead of Next
    expect(screen.getByText('Finish')).toBeInTheDocument();
    expect(screen.queryByText('Next')).not.toBeInTheDocument();
  });

  it('dismisses the guide when Skip Guide is clicked', () => {
    const onCloseMock = jest.fn();
    render(<QuickStartGuide onClose={onCloseMock} />);
    
    // Click Skip Guide
    fireEvent.click(screen.getByText('Skip Guide'));
    
    // Should mark the guide as dismissed and call onClose
    expect(localStorageMock.setItem).toHaveBeenCalledWith('cryptobot_quickstart_dismissed', 'true');
    expect(onCloseMock).toHaveBeenCalled();
  });

  it('dismisses the guide when the close button is clicked', () => {
    const onCloseMock = jest.fn();
    render(<QuickStartGuide onClose={onCloseMock} />);
    
    // Click the close button (X)
    fireEvent.click(screen.getByLabelText('Close'));
    
    // Should mark the guide as dismissed and call onClose
    expect(localStorageMock.setItem).toHaveBeenCalledWith('cryptobot_quickstart_dismissed', 'true');
    expect(onCloseMock).toHaveBeenCalled();
  });

  it('dismisses the guide when Finish is clicked on the last step', () => {
    const onCloseMock = jest.fn();
    render(<QuickStartGuide onClose={onCloseMock} />);
    
    // Navigate to the last step
    for (let i = 0; i < 4; i++) {
      fireEvent.click(screen.getByText('Next'));
    }
    
    // Click Finish
    fireEvent.click(screen.getByText('Finish'));
    
    // Should mark the guide as dismissed and call onClose
    expect(localStorageMock.setItem).toHaveBeenCalledWith('cryptobot_quickstart_dismissed', 'true');
    expect(onCloseMock).toHaveBeenCalled();
  });

  it('does not render if already dismissed', () => {
    // Set the guide as already dismissed
    localStorageMock.setItem('cryptobot_quickstart_dismissed', 'true');
    
    const { container } = render(<QuickStartGuide />);
    
    // Component should not render anything
    expect(container).toBeEmptyDOMElement();
  });

  it('resets dismissed state when resetDismissed is called', () => {
    // Set the guide as already dismissed
    localStorageMock.setItem('cryptobot_quickstart_dismissed', 'true');
    
    const { rerender } = render(<QuickStartGuide />);
    
    // Component should not render anything initially
    expect(screen.queryByText('Quick Start Guide')).not.toBeInTheDocument();
    
    // Get the component instance and call resetDismissed
    const resetDismissed = QuickStartGuide.prototype.resetDismissed;
    resetDismissed();
    
    // Re-render the component
    rerender(<QuickStartGuide />);
    
    // Component should now render
    expect(screen.getByText('Quick Start Guide')).toBeInTheDocument();
  });
});