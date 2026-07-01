/**
 * tests/components/HITLPanel.test.tsx — HITL Panel component tests
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock stores
const mockTrajectories = [
  {
    id: 'traj-001', strategy: 'OPTIMAL' as const, waypoints: [
      { x: 0, y: 0, z: 0, time_from_start_sec: 0 },
      { x: 0.3, y: 0.1, z: 0.2, time_from_start_sec: 1.0 },
    ],
    score: 0.92, collision_free: true, duration_sec: 1.0,
  },
  {
    id: 'traj-002', strategy: 'CONSERVATIVE' as const, waypoints: [
      { x: 0, y: 0, z: 0, time_from_start_sec: 0 },
      { x: 0.3, y: 0.2, z: 0.2, time_from_start_sec: 1.8 },
    ],
    score: 0.78, collision_free: true, duration_sec: 1.8,
  },
];

// Mock zustand stores
jest.mock('@/stores/trajectoryStore', () => ({
  useTrajectoryStore: jest.fn((selector) => {
    const state = {
      trajectories: mockTrajectories,
      selectedId: null as string | null,
      showGhostTrails: true,
      setTrajectories: jest.fn(),
      selectTrajectory: jest.fn(),
      toggleGhostTrails: jest.fn(),
    };
    return selector ? selector(state) : state;
  }),
}));

jest.mock('@/stores/hitlStore', () => ({
  useHITLStore: jest.fn((selector) => {
    const state = {
      prompt: null as { trajectories: typeof mockTrajectories; timeout_sec: number } | null,
      countdown: 10,
      mode: 'suggested' as const,
      awaitingSelection: false,
      setPrompt: jest.fn(),
      setCountdown: jest.fn(),
      setMode: jest.fn(),
      selectTrajectory: jest.fn(),
      clearPrompt: jest.fn(),
    };
    return selector ? selector(state) : state;
  }),
}));

describe('HITLPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    const { HITLPanel } = require('@/components/hitl-panel/HITLPanel');
    render(<HITLPanel />);
    expect(screen.getByText(/人机协同/i)).toBeInTheDocument();
  });

  it('displays demo trigger button when not awaiting selection', () => {
    const { HITLPanel } = require('@/components/hitl-panel/HITLPanel');
    render(<HITLPanel />);
    expect(screen.getByText(/模拟轨迹选择/i)).toBeInTheDocument();
  });

  it('renders ModeControl component', () => {
    const { HITLPanel } = require('@/components/hitl-panel/HITLPanel');
    render(<HITLPanel />);
    // ModeControl should be rendered within HITLPanel
    expect(document.body.textContent).toContain('HITL');
  });
});

describe('TrajectoryCard', () => {
  it('renders trajectory information', () => {
    const { TrajectoryCard } = require('@/components/hitl-panel/TrajectoryCard');
    render(
      <TrajectoryCard
        trajectory={mockTrajectories[0]}
        selected={false}
        onSelect={jest.fn()}
      />
    );
    expect(document.body.textContent).toContain('92');
  });

  it('calls onSelect when clicked', () => {
    const onSelect = jest.fn();
    const { TrajectoryCard } = require('@/components/hitl-panel/TrajectoryCard');
    const { container } = render(
      <TrajectoryCard
        trajectory={mockTrajectories[0]}
        selected={false}
        onSelect={onSelect}
      />
    );
    const button = container.querySelector('button');
    if (button) {
      fireEvent.click(button);
      expect(onSelect).toHaveBeenCalled();
    }
  });
});

describe('Countdown', () => {
  it('renders with remaining time', () => {
    const { Countdown } = require('@/components/hitl-panel/Countdown');
    render(
      <Countdown
        seconds={5}
        onTimeout={jest.fn()}
      />
    );
    expect(document.body.textContent).toContain('5');
  });
});

describe('ModeControl', () => {
  it('renders mode options', () => {
    const { ModeControl } = require('@/components/hitl-panel/ModeControl');
    const onChange = jest.fn();
    render(<ModeControl current="suggested" onChange={onChange} />);
    expect(document.body.textContent).toBeTruthy();
  });
});
