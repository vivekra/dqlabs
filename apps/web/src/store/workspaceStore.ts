'use client';

import { create } from 'zustand';

export type WorkspaceStatus =
  | 'provisioning'
  | 'running'
  | 'suspending'
  | 'suspended'
  | 'failed'
  | 'terminated';

export interface Workspace {
  id: string;
  name: string;
  status: WorkspaceStatus;
  ingress_url: string | null;
  namespace: string | null;
  pod_name: string | null;
  allocated_cpu: number;
  allocated_ram_mb: number;
  allocated_storage_gb: number;
  created_at: string;
  updated_at: string;
  template_id: string | null;
}

export interface LabTemplate {
  id: string;
  title: string;
  slug: string;
  description: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  category: string;
  is_active: boolean;
}

export interface UserSession {
  userId: string;
  email: string;
  activeTenantId: string;
  role: string;
  token: string;
}

export type AiMessage = { sender: 'ai' | 'user'; text: string; ts: number };

interface WorkspaceStore {
  // Session
  session: UserSession | null;
  setSession: (session: UserSession | null) => void;

  // Workspaces
  workspaces: Workspace[];
  selectedWorkspace: Workspace | null;
  isLoadingWorkspaces: boolean;
  workspaceError: string | null;
  setWorkspaces: (workspaces: Workspace[]) => void;
  setSelectedWorkspace: (ws: Workspace | null) => void;
  updateWorkspaceStatus: (id: string, status: WorkspaceStatus) => void;
  setLoadingWorkspaces: (loading: boolean) => void;
  setWorkspaceError: (error: string | null) => void;

  // Templates
  templates: LabTemplate[];
  isLoadingTemplates: boolean;
  setTemplates: (templates: LabTemplate[]) => void;
  setLoadingTemplates: (loading: boolean) => void;

  // UI State
  isSplitViewOpen: boolean;
  openSplitView: (ws: Workspace) => void;
  closeSplitView: () => void;

  activeTab: 'terminal' | 'logs' | 'events' | 'metrics';
  setActiveTab: (tab: 'terminal' | 'logs' | 'events' | 'metrics') => void;

  // AI Chat
  aiMessages: AiMessage[];
  addAiMessage: (sender: 'ai' | 'user', text: string) => void;
  clearAiMessages: () => void;

  // Mock Mode (enabled by default for safe local testing without a live cluster)
  mockMode: boolean;
  setMockMode: (v: boolean) => void;
}

export const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  session: null,
  setSession: (session) => set({ session }),

  workspaces: [],
  selectedWorkspace: null,
  isLoadingWorkspaces: false,
  workspaceError: null,
  setWorkspaces: (workspaces) => set({ workspaces }),
  setSelectedWorkspace: (ws) => set({ selectedWorkspace: ws }),
  updateWorkspaceStatus: (id, status) =>
    set((state) => ({
      workspaces: state.workspaces.map((w) => (w.id === id ? { ...w, status } : w)),
      selectedWorkspace:
        state.selectedWorkspace?.id === id
          ? { ...state.selectedWorkspace, status }
          : state.selectedWorkspace,
    })),
  setLoadingWorkspaces: (loading) => set({ isLoadingWorkspaces: loading }),
  setWorkspaceError: (error) => set({ workspaceError: error }),

  templates: [],
  isLoadingTemplates: false,
  setTemplates: (templates) => set({ templates }),
  setLoadingTemplates: (loading) => set({ isLoadingTemplates: loading }),

  isSplitViewOpen: false,
  openSplitView: (ws) => set({ isSplitViewOpen: true, selectedWorkspace: ws }),
  closeSplitView: () => set({ isSplitViewOpen: false }),

  activeTab: 'terminal',
  setActiveTab: (tab) => set({ activeTab: tab }),

  aiMessages: [
    {
      sender: 'ai',
      text: "Hi! I'm your AI infrastructure assistant. Ask me anything about your Kubernetes cluster or paste error logs for diagnosis.",
      ts: Date.now(),
    },
  ],
  addAiMessage: (sender, text) =>
    set((state) => ({
      aiMessages: [...state.aiMessages, { sender, text, ts: Date.now() }],
    })),
  clearAiMessages: () =>
    set({
      aiMessages: [
        { sender: 'ai', text: 'Chat cleared. How can I help you?', ts: Date.now() },
      ],
    }),

  mockMode: true,
  setMockMode: (v) => set({ mockMode: v }),
}));
