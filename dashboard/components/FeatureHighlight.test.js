/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import FeatureHighlight, { 
  FeatureHighlightTour, 
  isTourCompleted, 
  resetCompletedTours 
} from './FeatureHighlight';

// Mock getBoundingClientRect for target element
const mockGetBoundingClientRect = () => ({
  top: 100,
  left: 100,
  width: 200,
  height: 50,
  bottom: 150,
  right: 300
});

// Mock scrollIntoView
const mockScrollIntoView = jest.fn();

// Mock window dimensions
Object.defineProperty(window, 'innerWidth', { value: 1024 });
Object.defineProperty(window, 'innerHeight', { value: 768 });

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

describe('FeatureHighlight', () => {
  beforeEach(() => {
    localStorageMock.clear();
    jest.clearAllMocks();
    
    // Create a target element for the highlight
    const targetElement = document.createElement('div');
    targetElement.id = 'test-target';
    targetElement.textContent = 'Target Element';
    targetElement.getBoundingClientRect = mockGetBoundingClientRect;
    targetElement.scrollIntoView = mockScrollIntoView;
    document.body.appendChild(targetElement);
  });
  
  afterEach(() => {
    // Clean up the target element
    const targetElement = document.getElementById('test-target');
    if (targetElement) {
      document.body.removeChild(targetElement);
    }
  });

  it('renders the feature highlight with correct title and description', () => {
    const onDismiss = jest.fn();
    const onNext = jest.fn();
    
    render(
      <FeatureHighlight
        targetId="test-target"
        title="Test Feature"
        description="This is a test feature description"
        onDismiss={onDismiss}
        onNext={onNext}
      />
    );
    
    // Check that the title and description are rendered
    expect(screen.getByText('Test Feature')).toBeInTheDocument();
    expect(screen.getByText('This is a test feature description')).toBeInTheDocument();
    
    // Check that the buttons are rendered
    expect(screen.getByText('Skip all')).toBeInTheDocument();
    expect(screen.getByText('Next')).toBeInTheDocument();
  });

  it('shows "Finish" button when isLast is true', () => {
    render(
      <FeatureHighlight
        targetId="test-target"
        title="Test Feature"
        description="This is a test feature description"
        onDismiss={jest.fn()}
        onNext={jest.fn()}
        isLast={true}
      />
    );
    
    // Check that the Finish button is rendered instead of Next
    expect(screen.getByText('Finish')).toBeInTheDocument();
    expect(screen.queryByText('Next')).not.toBeInTheDocument();
  });

  it('calls onDismiss when Skip all button is clicked', () => {
    const onDismiss = jest.fn();
    
    render(
      <FeatureHighlight
        targetId="test-target"
        title="Test Feature"
        description="This is a test feature description"
        onDismiss={onDismiss}
        onNext={jest.fn()}
      />
    );
    
    // Click the Skip all button
    fireEvent.click(screen.getByText('Skip all'));
    
    // Check that onDismiss was called
    expect(onDismiss).toHaveBeenCalled();
  });

  it('calls onDismiss when close button is clicked', () => {
    const onDismiss = jest.fn();
    
    render(
      <FeatureHighlight
        targetId="test-target"
        title="Test Feature"
        description="This is a test feature description"
        onDismiss={onDismiss}
        onNext={jest.fn()}
      />
    );
    
    // Click the close button
    fireEvent.click(screen.getByLabelText('Close'));
    
    // Check that onDismiss was called
    expect(onDismiss).toHaveBeenCalled();
  });

  it('calls onNext when Next button is clicked', () => {
    const onNext = jest.fn();
    
    render(
      <FeatureHighlight
        targetId="test-target"
        title="Test Feature"
        description="This is a test feature description"
        onDismiss={jest.fn()}
        onNext={onNext}
      />
    );
    
    // Click the Next button
    fireEvent.click(screen.getByText('Next'));
    
    // Check that onNext was called
    expect(onNext).toHaveBeenCalled();
  });

  it('positions the description box based on position prop', () => {
    const { rerender } = render(
      <FeatureHighlight
        targetId="test-target"
        title="Test Feature"
        description="Description"
        position="top"
        onDismiss={jest.fn()}
        onNext={jest.fn()}
      />
    );
    
    // Get the description box
    const descriptionBox = screen.getByText('Test Feature').closest('div');
    
    // Check that the style includes bottom position for top placement
    expect(descriptionBox.style.bottom).toBeTruthy();
    
    // Rerender with bottom position
    rerender(
      <FeatureHighlight
        targetId="test-target"
        title="Test Feature"
        description="Description"
        position="bottom"
        onDismiss={jest.fn()}
        onNext={jest.fn()}
      />
    );
    
    // Check that the style includes top position for bottom placement
    expect(descriptionBox.style.top).toBeTruthy();
  });

  it('does not render if target element is not found', () => {
    const { container } = render(
      <FeatureHighlight
        targetId="non-existent-target"
        title="Test Feature"
        description="This is a test feature description"
        onDismiss={jest.fn()}
        onNext={jest.fn()}
      />
    );
    
    // Component should not render anything
    expect(container).toBeEmptyDOMElement();
  });
});

describe('FeatureHighlightTour', () => {
  beforeEach(() => {
    localStorageMock.clear();
    jest.clearAllMocks();
    
    // Create target elements for the tour
    const targetElement1 = document.createElement('div');
    targetElement1.id = 'target1';
    targetElement1.getBoundingClientRect = mockGetBoundingClientRect;
    targetElement1.scrollIntoView = mockScrollIntoView;
    document.body.appendChild(targetElement1);
    
    const targetElement2 = document.createElement('div');
    targetElement2.id = 'target2';
    targetElement2.getBoundingClientRect = mockGetBoundingClientRect;
    targetElement2.scrollIntoView = mockScrollIntoView;
    document.body.appendChild(targetElement2);
  });
  
  afterEach(() => {
    // Clean up the target elements
    const targetElement1 = document.getElementById('target1');
    if (targetElement1) {
      document.body.removeChild(targetElement1);
    }
    
    const targetElement2 = document.getElementById('target2');
    if (targetElement2) {
      document.body.removeChild(targetElement2);
    }
  });

  it('renders the first highlight in the tour', () => {
    const highlights = [
      {
        targetId: 'target1',
        title: 'Feature 1',
        description: 'Description 1',
        position: 'bottom'
      },
      {
        targetId: 'target2',
        title: 'Feature 2',
        description: 'Description 2',
        position: 'top'
      }
    ];
    
    render(
      <FeatureHighlightTour
        highlights={highlights}
        onComplete={jest.fn()}
        tourId="test-tour"
      />
    );
    
    // Check that the first highlight is rendered
    expect(screen.getByText('Feature 1')).toBeInTheDocument();
    expect(screen.getByText('Description 1')).toBeInTheDocument();
    
    // Second highlight should not be visible yet
    expect(screen.queryByText('Feature 2')).not.toBeInTheDocument();
  });

  it('navigates to the next highlight when Next is clicked', () => {
    const highlights = [
      {
        targetId: 'target1',
        title: 'Feature 1',
        description: 'Description 1',
        position: 'bottom'
      },
      {
        targetId: 'target2',
        title: 'Feature 2',
        description: 'Description 2',
        position: 'top'
      }
    ];
    
    render(
      <FeatureHighlightTour
        highlights={highlights}
        onComplete={jest.fn()}
        tourId="test-tour"
      />
    );
    
    // Click the Next button
    fireEvent.click(screen.getByText('Next'));
    
    // Check that the second highlight is now rendered
    expect(screen.getByText('Feature 2')).toBeInTheDocument();
    expect(screen.getByText('Description 2')).toBeInTheDocument();
    
    // First highlight should no longer be visible
    expect(screen.queryByText('Feature 1')).not.toBeInTheDocument();
  });

  it('completes the tour when Finish is clicked on the last highlight', () => {
    const onComplete = jest.fn();
    const highlights = [
      {
        targetId: 'target1',
        title: 'Feature 1',
        description: 'Description 1'
      },
      {
        targetId: 'target2',
        title: 'Feature 2',
        description: 'Description 2'
      }
    ];
    
    render(
      <FeatureHighlightTour
        highlights={highlights}
        onComplete={onComplete}
        tourId="test-tour"
      />
    );
    
    // Navigate to the last highlight
    fireEvent.click(screen.getByText('Next'));
    
    // Click the Finish button
    fireEvent.click(screen.getByText('Finish'));
    
    // Check that onComplete was called
    expect(onComplete).toHaveBeenCalled();
    
    // Check that the tour was marked as completed
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'cryptobot_completed_tours',
      JSON.stringify(['test-tour'])
    );
  });

  it('dismisses the tour when Skip all is clicked', () => {
    const onComplete = jest.fn();
    const highlights = [
      {
        targetId: 'target1',
        title: 'Feature 1',
        description: 'Description 1'
      },
      {
        targetId: 'target2',
        title: 'Feature 2',
        description: 'Description 2'
      }
    ];
    
    render(
      <FeatureHighlightTour
        highlights={highlights}
        onComplete={onComplete}
        tourId="test-tour"
      />
    );
    
    // Click the Skip all button
    fireEvent.click(screen.getByText('Skip all'));
    
    // Check that onComplete was called
    expect(onComplete).toHaveBeenCalled();
    
    // Check that the tour was marked as completed
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'cryptobot_completed_tours',
      JSON.stringify(['test-tour'])
    );
  });

  it('does not render if the tour has already been completed', () => {
    // Mark the tour as already completed
    localStorageMock.setItem('cryptobot_completed_tours', JSON.stringify(['test-tour']));
    
    const highlights = [
      {
        targetId: 'target1',
        title: 'Feature 1',
        description: 'Description 1'
      }
    ];
    
    const { container } = render(
      <FeatureHighlightTour
        highlights={highlights}
        onComplete={jest.fn()}
        tourId="test-tour"
      />
    );
    
    // Component should not render anything
    expect(container).toBeEmptyDOMElement();
  });

  it('does not render if highlights array is empty', () => {
    const { container } = render(
      <FeatureHighlightTour
        highlights={[]}
        onComplete={jest.fn()}
        tourId="test-tour"
      />
    );
    
    // Component should not render anything
    expect(container).toBeEmptyDOMElement();
  });
});

describe('isTourCompleted', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('returns true if tour is in completed list', () => {
    // Set completed tours
    localStorageMock.setItem('cryptobot_completed_tours', JSON.stringify(['tour1', 'tour2']));
    
    expect(isTourCompleted('tour1')).toBe(true);
  });
  
  it('returns false if tour is not in completed list', () => {
    // Set completed tours
    localStorageMock.setItem('cryptobot_completed_tours', JSON.stringify(['tour1', 'tour2']));
    
    expect(isTourCompleted('tour3')).toBe(false);
  });
  
  it('returns false if no tours are completed', () => {
    expect(isTourCompleted('tour1')).toBe(false);
  });
});

describe('resetCompletedTours', () => {
  it('removes all completed tours from localStorage', () => {
    // Set completed tours
    localStorageMock.setItem('cryptobot_completed_tours', JSON.stringify(['tour1', 'tour2']));
    
    resetCompletedTours();
    
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('cryptobot_completed_tours');
  });
});