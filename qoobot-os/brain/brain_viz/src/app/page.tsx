/**
 * src/app/page.tsx — Main Dashboard page
 *
 * Layout: Sidebar + 3D Scene View + Right Panel (chat/hitl/status/dev)
 * Integrates all providers and WebSocket lifecycle.
 */
'use client';

import { useEffect } from 'react';
import { DashboardShell } from '@/components/dashboard/DashboardShell';
import { SceneView } from '@/components/scene-view/SceneView';
import { ChatPanel } from '@/components/chat-panel/ChatPanel';
import { HITLPanel } from '@/components/hitl-panel/HITLPanel';
import { StatusMonitor } from '@/components/status-monitor/StatusMonitor';
import { DevPanel } from '@/components/dev-panel/DevPanel';
import { ToastProvider } from '@/components/common/Toast';
import { AuthProvider } from '@/components/dashboard/AuthProvider';
import { ThemeProvider } from '@/components/dashboard/ThemeProvider';
import { LayoutManager } from '@/components/dashboard/LayoutManager';
import { useUIStore } from '@/stores/uiStore';
import { wsClient } from '@/services/wsClient';
import { useRobotStore } from '@/stores/robotStore';
import { useSceneStore } from '@/stores/sceneStore';
import { useTrajectoryStore } from '@/stores/trajectoryStore';
import { useHITLStore } from '@/stores/hitlStore';
import { useMonitorStore } from '@/stores/monitorStore';
import { useKeyboardControls } from '@/hooks/useKeyboardControls';

function RightPanel() {
  const activePanel = useUIStore((s) => s.activePanel);

  switch (activePanel) {
    case 'chat':   return <ChatPanel />;
    case 'hitl':   return <HITLPanel />;
    case 'status': return <StatusMonitor />;
    case 'dev':    return <DevPanel />;
    default:       return <ChatPanel />;
  }
}

function DashboardContent() {
  const setConnected = useRobotStore((s) => s.setConnected);
  const updateScene  = useSceneStore((s) => s.updateScene);
  const setTrajectories = useTrajectoryStore((s) => s.setTrajectories);
  const setPrompt    = useHITLStore((s) => s.setPrompt);
  const setSafety    = useMonitorStore((s) => s.setSafety);

  // Enable keyboard shortcuts
  useKeyboardControls();

  useEffect(() => {
    // Connect to brain_ai WebSocket
    wsClient.connect();

    // Scene updates from perception
    wsClient.on('scene_update', (event) => {
      updateScene(event.payload as any);
    });

    // Ghost trails from decision/planning
    wsClient.on('ghost_trail', (event) => {
      const payload = event.payload as any;
      if (payload.trajectories) {
        setTrajectories(payload.trajectories);
      }
    });

    // HITL prompts when human input is needed
    wsClient.on('hitl_prompt', (event) => {
      setPrompt(event.payload as any);
    });

    // Robot connection state
    wsClient.on('robot_state', (event) => {
      setConnected(true);
      const payload = event.payload as any;
      if (payload.safety) {
        setSafety(payload.safety);
      }
    });

    // Safety alerts
    wsClient.on('safety_alert', (event) => {
      const payload = event.payload as any;
      if (payload) {
        setSafety(payload);
      }
    });

    // Task status updates
    wsClient.on('task_status', (event) => {
      const payload = event.payload as any;
      // TODO: Update chat store with task status changes
      console.log('[Dashboard] Task status:', payload);
    });

    return () => {
      wsClient.disconnect();
    };
  }, [setConnected, updateScene, setTrajectories, setPrompt, setSafety]);

  return (
    <DashboardShell>
      <div className="flex-1 relative">
        <SceneView />
      </div>
      <div className="w-96 border-l border-brain-border overflow-y-auto">
        <RightPanel />
      </div>
    </DashboardShell>
  );
}

export default function DashboardPage() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <ToastProvider>
          <LayoutManager>
            <DashboardContent />
          </LayoutManager>
        </ToastProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}
