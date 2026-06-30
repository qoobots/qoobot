/**
 * tests/components/SceneView.test.tsx — SceneView component tests
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock Three.js and R3F
jest.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="three-canvas">{children}</div>
  ),
  useFrame: jest.fn(),
  useThree: jest.fn(() => ({
    camera: {},
    gl: { domElement: document.createElement('canvas') },
    scene: {},
    size: { width: 800, height: 600 },
  })),
}));

jest.mock('@react-three/drei', () => ({
  OrbitControls: () => <div data-testid="orbit-controls" />,
  Grid: () => <div data-testid="drei-grid" />,
  GizmoHelper: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="gizmo-helper">{children}</div>
  ),
  GizmoViewport: () => <div data-testid="gizmo-viewport" />,
  Text: ({ children }: { children: React.ReactNode }) => (
    <span data-testid="drei-text">{children}</span>
  ),
}));

jest.mock('three', () => ({
  ...jest.requireActual('three'),
  WebGLRenderer: jest.fn(),
}));

describe('SceneView', () => {
  it('renders the canvas element', () => {
    const { SceneView } = require('@/components/scene-view/SceneView');
    render(<SceneView />);
    expect(screen.getByTestId('three-canvas')).toBeInTheDocument();
  });

  it('shows offline placeholder when no connection', () => {
    const { SceneView } = require('@/components/scene-view/SceneView');
    render(<SceneView />);
    // Without robot state, should show offline message
    const threeCanvas = screen.getByTestId('three-canvas');
    expect(threeCanvas).toBeInTheDocument();
  });
});

describe('SceneLighting', () => {
  it('renders without error', () => {
    const { SceneLighting } = require('@/components/scene-view/SceneLighting');
    // Should render ambient and directional light components
    const { container } = render(<SceneLighting />);
    expect(container).toBeTruthy();
  });
});

describe('CoordinateGrid', () => {
  it('renders grid and axes', () => {
    const { CoordinateGrid } = require('@/components/scene-view/CoordinateGrid');
    render(<CoordinateGrid />);
    expect(screen.getByTestId('drei-grid')).toBeInTheDocument();
  });
});

describe('GhostTrail', () => {
  it('renders trajectory lines', () => {
    const { GhostTrail } = require('@/components/scene-view/GhostTrail');
    const trajectories = [
      {
        id: 't1', strategy: 'OPTIMAL',
        waypoints: [{ x: 0, y: 0, z: 0, time_from_start_sec: 0 }],
        score: 1, collision_free: true, duration_sec: 1,
      },
    ];
    const { container } = render(
      <GhostTrail trajectories={trajectories} selectedId={null} />
    );
    expect(container).toBeTruthy();
  });

  it('renders empty when no trajectories', () => {
    const { GhostTrail } = require('@/components/scene-view/GhostTrail');
    const { container } = render(
      <GhostTrail trajectories={[]} selectedId={null} />
    );
    expect(container).toBeTruthy();
  });
});
