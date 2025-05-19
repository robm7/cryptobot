/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import HelpTooltip, { 
  isTooltipDismissed, 
  resetDismissedTooltips 
} from './HelpTooltip';
import * as firstRunUtils from '../utils/firstRunUtils';

// Mock the firstRunUtils
jest.mock('../utils/firstRunUtils', () => ({
  getSetupPreferences: jest.fn(() => ({ showTooltips: true }))
}));

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

describe('HelpTooltip', () => {
  beforeEach(() => {
    localStorageMock.clear();
    jest.clearAllMocks();
  });

  it('renders children without tooltip initially', () => {
    render(
      <HelpTooltip id="test-tooltip" content="Test tooltip content">
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Child element should be rendered
    expect(screen.getByText('Hover me')).toBeInTheDocument();
    
    // Tooltip should not be visible initially
    expect(screen.queryByText('Test tooltip content')).not.toBeInTheDocument();
  });

  it('shows tooltip on hover', () => {
    render(
      <HelpTooltip id="test-tooltip" content="Test tooltip content">
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Hover over the element
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // Tooltip should now be visible
    expect(screen.getByText('Test tooltip content')).toBeInTheDocument();
    expect(screen.getByText('Help')).toBeInTheDocument();
  });

  it('hides tooltip on mouse leave', () => {
    render(
      <HelpTooltip id="test-tooltip" content="Test tooltip content">
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Hover over the element
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // Tooltip should be visible
    expect(screen.getByText('Test tooltip content')).toBeInTheDocument();
    
    // Move mouse away
    fireEvent.mouseLeave(screen.getByText('Hover me'));
    
    // Tooltip should be hidden
    expect(screen.queryByText('Test tooltip content')).not.toBeInTheDocument();
  });

  it('dismisses tooltip when dismiss button is clicked', () => {
    render(
      <HelpTooltip id="test-tooltip" content="Test tooltip content">
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Hover over the element
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // Click the dismiss button
    fireEvent.click(screen.getByLabelText('Dismiss'));
    
    // Tooltip should be hidden
    expect(screen.queryByText('Test tooltip content')).not.toBeInTheDocument();
    
    // Tooltip ID should be stored in localStorage
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'cryptobot_dismissed_tooltips',
      JSON.stringify(['test-tooltip'])
    );
    
    // Hover again
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // Tooltip should still be hidden because it was dismissed
    expect(screen.queryByText('Test tooltip content')).not.toBeInTheDocument();
  });

  it('does not show tooltip if tooltips are disabled in preferences', () => {
    // Mock preferences with tooltips disabled
    firstRunUtils.getSetupPreferences.mockReturnValueOnce({ showTooltips: false });
    
    render(
      <HelpTooltip id="test-tooltip" content="Test tooltip content">
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Hover over the element
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // Tooltip should not be visible
    expect(screen.queryByText('Test tooltip content')).not.toBeInTheDocument();
  });

  it('shows tooltip if forceShow is true, even if tooltips are disabled', () => {
    // Mock preferences with tooltips disabled
    firstRunUtils.getSetupPreferences.mockReturnValueOnce({ showTooltips: false });
    
    render(
      <HelpTooltip id="test-tooltip" content="Test tooltip content" forceShow={true}>
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Hover over the element
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // Tooltip should be visible because forceShow is true
    expect(screen.getByText('Test tooltip content')).toBeInTheDocument();
  });

  it('shows tooltip if forceShow is true, even if it was dismissed', () => {
    // Set the tooltip as already dismissed
    localStorageMock.setItem('cryptobot_dismissed_tooltips', JSON.stringify(['test-tooltip']));
    
    render(
      <HelpTooltip id="test-tooltip" content="Test tooltip content" forceShow={true}>
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Hover over the element
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // Tooltip should be visible because forceShow is true
    expect(screen.getByText('Test tooltip content')).toBeInTheDocument();
  });

  it('positions tooltip correctly based on position prop', () => {
    const { rerender } = render(
      <HelpTooltip id="test-tooltip" content="Test content" position="top">
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Hover over the element
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // Get the tooltip element
    const tooltip = screen.getByText('Test content').closest('div');
    
    // Check top position classes
    expect(tooltip.className).toContain('bottom-full');
    
    // Rerender with right position
    rerender(
      <HelpTooltip id="test-tooltip" content="Test content" position="right">
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Check right position classes
    expect(tooltip.className).toContain('left-full');
    
    // Rerender with bottom position
    rerender(
      <HelpTooltip id="test-tooltip" content="Test content" position="bottom">
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Check bottom position classes
    expect(tooltip.className).toContain('top-full');
    
    // Rerender with left position
    rerender(
      <HelpTooltip id="test-tooltip" content="Test content" position="left">
        <button>Hover me</button>
      </HelpTooltip>
    );
    
    // Check left position classes
    expect(tooltip.className).toContain('right-full');
  });

  describe('isTooltipDismissed', () => {
    it('returns true if tooltip is in dismissed list', () => {
      // Set dismissed tooltips
      localStorageMock.setItem('cryptobot_dismissed_tooltips', JSON.stringify(['tooltip1', 'tooltip2']));
      
      expect(isTooltipDismissed('tooltip1')).toBe(true);
    });
    
    it('returns false if tooltip is not in dismissed list', () => {
      // Set dismissed tooltips
      localStorageMock.setItem('cryptobot_dismissed_tooltips', JSON.stringify(['tooltip1', 'tooltip2']));
      
      expect(isTooltipDismissed('tooltip3')).toBe(false);
    });
    
    it('returns false if no tooltips are dismissed', () => {
      expect(isTooltipDismissed('tooltip1')).toBe(false);
    });
  });

  describe('resetDismissedTooltips', () => {
    it('removes all dismissed tooltips from localStorage', () => {
      // Set dismissed tooltips
      localStorageMock.setItem('cryptobot_dismissed_tooltips', JSON.stringify(['tooltip1', 'tooltip2']));
      
      resetDismissedTooltips();
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('cryptobot_dismissed_tooltips');
    });
  });
});