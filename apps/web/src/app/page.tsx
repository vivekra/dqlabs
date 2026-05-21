'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Terminal,
  Code,
  Activity,
  Cpu,
  Database,
  HardDrive,
  Bot,
  ChevronRight,
  Play,
  RefreshCw,
  Shield,
  Users,
  Layers,
  Network,
  Sliders,
  Settings,
  Search,
  Plus,
  Sparkles,
  Compass,
  FolderLock,
  Cloud,
  FileText,
  ExternalLink,
  ChevronDown,
  Pause,
  Square,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  X,
  Send,
  ToggleLeft,
  ToggleRight,
  Zap,
  ServerCrash,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import { useWorkspaceStore, Workspace, WorkspaceStatus } from '../store/workspaceStore';
import { api, MOCK_WORKSPACES, MOCK_TEMPLATES, buildTerminalWsUrl } from '../lib/api';

// Dynamically load heavy split-view to avoid SSR
const WorkspaceSplitView = dynamic(() => import('../components/WorkspaceSplitView'), {
  ssr: false,
});
const XtermTerminal = dynamic(() => import('../components/XtermTerminal'), {
  ssr: false,
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusColor(status: WorkspaceStatus) {
  switch (status) {
    case 'running': return 'text-emerald-400';
    case 'provisioning': return 'text-yellow-400';
    case 'suspending': return 'text-orange-400';
    case 'suspended': return 'text-slate-400';
    case 'failed': return 'text-red-400';
    case 'terminated': return 'text-red-600';
    default: return 'text-slate-500';
  }
}

function statusBadge(status: WorkspaceStatus) {
  switch (status) {
    case 'running': return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400';
    case 'provisioning': return 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400';
    case 'suspending': return 'bg-orange-500/10 border-orange-500/30 text-orange-400';
    case 'suspended': return 'bg-slate-500/10 border-slate-500/30 text-slate-400';
    case 'failed': return 'bg-red-500/10 border-red-500/30 text-red-400';
    case 'terminated': return 'bg-red-900/10 border-red-800/30 text-red-600';
    default: return 'bg-slate-800 border-slate-700 text-slate-500';
  }
}

function statusIcon(status: WorkspaceStatus) {
  switch (status) {
    case 'running': return <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />;
    case 'provisioning': return <Loader2 className="h-3 w-3 animate-spin text-yellow-400" />;
    case 'suspending': return <Loader2 className="h-3 w-3 animate-spin text-orange-400" />;
    case 'suspended': return <Pause className="h-3 w-3 text-slate-400" />;
    case 'failed': return <ServerCrash className="h-3 w-3 text-red-400" />;
    case 'terminated': return <X className="h-3 w-3 text-red-600" />;
    default: return null;
  }
}

function diffNow(iso: string) {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ── Launch Workspace Modal ────────────────────────────────────────────────────

function LaunchModal({
  templates,
  onLaunch,
  onClose,
}: {
  templates: import('../store/workspaceStore').LabTemplate[];
  onLaunch: (templateId: string, name: string) => Promise<void>;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState(templates[0]?.id ?? '');
  const [name, setName] = useState('');
  const [launching, setLaunching] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || !name.trim()) return;
    setLaunching(true);
    try {
      await onLaunch(selected, name.trim());
      onClose();
    } finally {
      setLaunching(false);
    }
  };

  const difficultyColor = (d: string) =>
    d === 'beginner' ? 'text-emerald-400' : d === 'intermediate' ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ scale: 0.95, opacity: 0, y: 10 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="relative w-full max-w-lg rounded-2xl bg-[#07091e] border border-[#1d2d5c] shadow-2xl shadow-purple-900/30 overflow-hidden"
      >
        {/* Header */}
        <div className="p-5 border-b border-[#152345] flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">Launch New Workspace</h2>
            <p className="text-xs text-slate-500 mt-0.5">Choose a lab template and name your environment</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-800 transition text-slate-500">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Name */}
          <div>
            <label className="text-xs font-semibold text-slate-400 block mb-1.5 uppercase tracking-wider">Workspace Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. My K8s Playground"
              required
              className="w-full bg-[#0a0f28] border border-[#1d2d5c] rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 transition"
            />
          </div>

          {/* Template selector */}
          <div>
            <label className="text-xs font-semibold text-slate-400 block mb-1.5 uppercase tracking-wider">Lab Template</label>
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {templates.map((tpl) => (
                <button
                  key={tpl.id}
                  type="button"
                  onClick={() => setSelected(tpl.id)}
                  className={`w-full text-left p-3 rounded-xl border transition ${
                    selected === tpl.id
                      ? 'bg-purple-600/10 border-purple-500/50 ring-1 ring-purple-500/20'
                      : 'bg-[#0a0f28] border-[#1d2d5c] hover:border-[#2d4080] hover:bg-[#0f1535]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-200">{tpl.title}</span>
                    <span className={`text-[10px] font-bold uppercase ${difficultyColor(tpl.difficulty)}`}>
                      {tpl.difficulty}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{tpl.description}</p>
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={launching || !selected || !name.trim()}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm shadow-lg shadow-purple-900/40 transition"
          >
            {launching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            {launching ? 'Launching…' : 'Launch Workspace'}
          </button>
        </form>
      </motion.div>
    </div>
  );
}

// ── Workspace Card ────────────────────────────────────────────────────────────

function WorkspaceCard({
  ws,
  onOpen,
  onSuspend,
  onResume,
  onTerminate,
}: {
  ws: Workspace;
  onOpen: () => void;
  onSuspend: () => void;
  onResume: () => void;
  onTerminate: () => void;
}) {
  const [confirmTerminate, setConfirmTerminate] = useState(false);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      className="p-4 rounded-xl bg-gradient-to-b from-[#090d22] to-[#050817] border border-[#152345] hover:border-[#2d3f70] transition-all group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          {statusIcon(ws.status)}
          <h3 className="text-sm font-bold text-white truncate">{ws.name}</h3>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold uppercase tracking-wider shrink-0 ml-2 ${statusBadge(ws.status)}`}>
          {ws.status}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="p-2 rounded-lg bg-[#040819] border border-[#111c3a] text-center">
          <span className="text-[9px] text-slate-500 block uppercase tracking-wider">CPU</span>
          <span className="text-xs font-bold text-slate-200">{ws.allocated_cpu} vCPU</span>
        </div>
        <div className="p-2 rounded-lg bg-[#040819] border border-[#111c3a] text-center">
          <span className="text-[9px] text-slate-500 block uppercase tracking-wider">RAM</span>
          <span className="text-xs font-bold text-slate-200">{(ws.allocated_ram_mb / 1024).toFixed(0)} GB</span>
        </div>
        <div className="p-2 rounded-lg bg-[#040819] border border-[#111c3a] text-center">
          <span className="text-[9px] text-slate-500 block uppercase tracking-wider">Disk</span>
          <span className="text-xs font-bold text-slate-200">{ws.allocated_storage_gb} GB</span>
        </div>
      </div>

      {ws.ingress_url && (
        <a
          href={ws.ingress_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300 mb-3 truncate"
        >
          <ExternalLink className="h-2.5 w-2.5 shrink-0" />
          <span className="truncate">{ws.ingress_url}</span>
        </a>
      )}

      <div className="flex items-center justify-between">
        <span className="text-[10px] text-slate-600">{diffNow(ws.updated_at)}</span>

        <div className="flex items-center gap-1.5">
          {ws.status === 'running' && (
            <button
              onClick={onOpen}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-purple-600/10 border border-purple-500/30 text-purple-400 hover:bg-purple-600/20 text-[10px] font-semibold transition"
            >
              <Terminal className="h-3 w-3" />
              Open
            </button>
          )}
          {ws.status === 'running' && (
            <button
              onClick={onSuspend}
              className="p-1.5 rounded-lg bg-[#0a0f28] border border-[#1d2d5c] text-slate-400 hover:text-orange-400 hover:border-orange-500/30 transition"
              title="Suspend"
            >
              <Pause className="h-3 w-3" />
            </button>
          )}
          {ws.status === 'suspended' && (
            <button
              onClick={onResume}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-600/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-600/20 text-[10px] font-semibold transition"
            >
              <Play className="h-3 w-3" />
              Resume
            </button>
          )}
          {(ws.status === 'failed' || ws.status === 'suspended' || ws.status === 'running') && (
            confirmTerminate ? (
              <div className="flex items-center gap-1">
                <span className="text-[9px] text-red-400">Sure?</span>
                <button
                  onClick={() => { onTerminate(); setConfirmTerminate(false); }}
                  className="px-1.5 py-0.5 rounded bg-red-600/20 border border-red-500/30 text-red-400 text-[9px] font-bold hover:bg-red-600/40 transition"
                >Yes</button>
                <button
                  onClick={() => setConfirmTerminate(false)}
                  className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400 text-[9px] font-bold hover:bg-slate-700 transition"
                >No</button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmTerminate(true)}
                className="p-1.5 rounded-lg bg-[#0a0f28] border border-[#1d2d5c] text-slate-500 hover:text-red-400 hover:border-red-500/30 transition"
                title="Terminate"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            )
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────

export default function WorkspaceDashboard() {
  const store = useWorkspaceStore();
  const {
    workspaces, setWorkspaces, updateWorkspaceStatus, isLoadingWorkspaces, setLoadingWorkspaces,
    templates, setTemplates,
    aiMessages, addAiMessage,
    isSplitViewOpen, openSplitView, closeSplitView, selectedWorkspace,
    activeTab, setActiveTab,
    mockMode, setMockMode,
    session,
  } = store;

  const [activeNav, setActiveNav] = useState('overview');
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [showLaunchModal, setShowLaunchModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const aiScrollRef = useRef<HTMLDivElement>(null);

  // ── Load data ──────────────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    setLoadingWorkspaces(true);
    try {
      if (mockMode) {
        await new Promise((r) => setTimeout(r, 400)); // simulate network
        setWorkspaces(MOCK_WORKSPACES);
        setTemplates(MOCK_TEMPLATES);
      } else if (session) {
        const [wsList, tplList] = await Promise.all([
          api.listWorkspaces(session.token, session.activeTenantId),
          api.listTemplates(session.token, session.activeTenantId),
        ]);
        setWorkspaces(wsList);
        setTemplates(tplList);
      }
    } catch (e) {
      console.error('Failed to load data:', e);
    } finally {
      setLoadingWorkspaces(false);
    }
  }, [mockMode, session, setWorkspaces, setTemplates, setLoadingWorkspaces]);

  useEffect(() => { loadData(); }, [loadData]);

  // Auto-scroll AI chat
  useEffect(() => {
    if (aiScrollRef.current) {
      aiScrollRef.current.scrollTop = aiScrollRef.current.scrollHeight;
    }
  }, [aiMessages]);

  // ── Workspace actions ──────────────────────────────────────────────────────
  const handleLaunch = async (templateId: string, name: string) => {
    if (mockMode) {
      const newWs: Workspace = {
        id: crypto.randomUUID(),
        name,
        status: 'provisioning',
        ingress_url: null,
        namespace: 'dq-tenant1',
        pod_name: null,
        allocated_cpu: 2,
        allocated_ram_mb: 4096,
        allocated_storage_gb: 20,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        template_id: templateId,
      };
      setWorkspaces([newWs, ...workspaces]);
      // Simulate provisioning completion
      setTimeout(() => updateWorkspaceStatus(newWs.id, 'running'), 4000);
      return;
    }
    if (!session) return;
    const ws = await api.createWorkspace(session.token, session.activeTenantId, {
      template_id: templateId, name,
      allocated_cpu: 2, allocated_ram_mb: 4096, allocated_storage_gb: 20,
    });
    setWorkspaces([ws, ...workspaces]);
  };

  const handleSuspend = async (ws: Workspace) => {
    if (mockMode) { updateWorkspaceStatus(ws.id, 'suspending'); setTimeout(() => updateWorkspaceStatus(ws.id, 'suspended'), 2000); return; }
    if (!session) return;
    updateWorkspaceStatus(ws.id, 'suspending');
    await api.updateWorkspace(session.token, session.activeTenantId, ws.id, { status: 'suspending' });
  };

  const handleResume = async (ws: Workspace) => {
    if (mockMode) { updateWorkspaceStatus(ws.id, 'provisioning'); setTimeout(() => updateWorkspaceStatus(ws.id, 'running'), 4000); return; }
    if (!session) return;
    updateWorkspaceStatus(ws.id, 'provisioning');
    await api.updateWorkspace(session.token, session.activeTenantId, ws.id, { status: 'running' });
  };

  const handleTerminate = async (ws: Workspace) => {
    if (mockMode) { updateWorkspaceStatus(ws.id, 'terminated'); return; }
    if (!session) return;
    await api.updateWorkspace(session.token, session.activeTenantId, ws.id, { status: 'terminated' });
    updateWorkspaceStatus(ws.id, 'terminated');
  };

  // ── AI chat ────────────────────────────────────────────────────────────────
  const handleSendAi = async (text: string) => {
    if (!text.trim() || aiLoading) return;
    setAiInput('');
    addAiMessage('user', text);
    setAiLoading(true);
    try {
      if (mockMode) {
        await new Promise((r) => setTimeout(r, 900));
        const responses: Record<string, string> = {
          crashing: "Analyzing cluster logs… Pod 'worker-7f9c8d7f6-ptulo' is in **CrashLoopBackOff**. The container exits immediately with exit code 1. Likely causes:\n1. Missing environment variable `DATABASE_URL`\n2. Cannot connect to postgres on port 5432\n\nRun `kubectl describe pod worker-7f9c8d7f6-ptulo -n backend` to see detailed events.",
          crashloop: "**CrashLoopBackOff** means the pod starts, crashes, and Kubernetes keeps restarting it. The back-off delay grows exponentially (10s → 20s → 40s…). Common causes:\n• App exits immediately (check logs)\n• Missing ConfigMap/Secret\n• OOMKilled (increase memory limit)",
          cpu: "Your cluster is currently at **42% CPU utilization** (2.1 / 5.0 vCPU). The `frontend` namespace is the heaviest consumer. Consider horizontal pod autoscaling with `kubectl autoscale deployment frontend --cpu-percent=70 --min=2 --max=6`.",
        };
        const key = Object.keys(responses).find((k) => text.toLowerCase().includes(k));
        addAiMessage('ai', key ? responses[key] : `Analyzing "${text}"… Running diagnostics on your cluster state. I recommend checking resource quotas and pod events first with:\n\`kubectl get events -A --sort-by=.metadata.creationTimestamp\``);
        return;
      }
      const res = await api.diagnose(text);
      addAiMessage('ai', `${res.diagnosis}\n\n**Suggested command:** \`${res.correction_command}\`\n\n_Source: ${res.source} (${res.model})_`);
    } catch {
      addAiMessage('ai', 'I encountered an error reaching the AI gateway. Please check that the AI service is running on port 8001.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleSuggestion = (suggestion: string) => handleSendAi(suggestion);

  // Filtered workspaces
  const visibleWorkspaces = workspaces.filter(
    (ws) => ws.status !== 'terminated' && (
      !searchQuery || ws.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
  );
  const runningCount = workspaces.filter((w) => w.status === 'running').length;
  const suspendedCount = workspaces.filter((w) => w.status === 'suspended').length;
  const totalCpu = workspaces.filter((w) => w.status === 'running').reduce((a, w) => a + w.allocated_cpu, 0);
  const totalRam = workspaces.filter((w) => w.status === 'running').reduce((a, w) => a + w.allocated_ram_mb, 0);

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen bg-[#02050f] text-slate-100 overflow-hidden font-sans text-xs">

      {/* ── Split view overlay ─────────────────────────────────────────────── */}
      <AnimatePresence>
        {isSplitViewOpen && selectedWorkspace && (
          <WorkspaceSplitView
            workspace={selectedWorkspace}
            token={session?.token}
            onClose={closeSplitView}
          />
        )}
      </AnimatePresence>

      {/* ── Launch modal ───────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showLaunchModal && (
          <LaunchModal
            templates={templates.length > 0 ? templates : MOCK_TEMPLATES}
            onLaunch={handleLaunch}
            onClose={() => setShowLaunchModal(false)}
          />
        )}
      </AnimatePresence>

      {/* ══════════════════════════════════════════════════════════════════════
          1. LEFT SIDEBAR
      ══════════════════════════════════════════════════════════════════════ */}
      <aside className="w-56 bg-[#04091e] border-r border-[#152345] flex flex-col justify-between select-none shrink-0">
        <div>
          {/* Logo */}
          <div className="h-14 px-4 flex items-center border-b border-[#152345]">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <div>
                <span className="font-bold text-sm tracking-tight text-white block">DigitalQ Labs</span>
                <span className="text-[9px] text-slate-400 block -mt-0.5">AI Workspace Engine</span>
              </div>
            </div>
          </div>

          {/* Mock mode toggle */}
          <div className="mx-3 mt-3 mb-1 p-2 rounded-lg bg-[#0e1633] border border-[#1d2d5c] flex items-center justify-between">
            <div>
              <span className="text-[10px] font-semibold text-slate-400 block">Mock Mode</span>
              <span className="text-[9px] text-slate-600">No live cluster needed</span>
            </div>
            <button onClick={() => setMockMode(!mockMode)}>
              {mockMode
                ? <ToggleRight className="h-5 w-5 text-yellow-400" />
                : <ToggleLeft className="h-5 w-5 text-slate-500" />
              }
            </button>
          </div>

          {/* Nav */}
          <nav className="px-2 mt-3 space-y-4">
            {[
              {
                section: 'Main', items: [
                  { id: 'overview', icon: Compass, label: 'Overview' },
                  { id: 'workspaces', icon: Cloud, label: 'Workspaces', badge: runningCount > 0 ? `${runningCount} live` : undefined },
                  { id: 'templates', icon: FileText, label: 'Templates' },
                  { id: 'environments', icon: Layers, label: 'Environments' },
                  { id: 'volumes', icon: HardDrive, label: 'Volumes' },
                  { id: 'secrets', icon: FolderLock, label: 'Secrets' },
                ]
              },
              {
                section: 'Collaboration', items: [
                  { id: 'team', icon: Users, label: 'Team' },
                  { id: 'activity', icon: Activity, label: 'Activity' },
                ]
              },
              {
                section: 'Tools', items: [
                  { id: 'ai', icon: Bot, label: 'AI Assistant', accent: true },
                  { id: 'terminal', icon: Terminal, label: 'Terminal' },
                  { id: 'settings', icon: Settings, label: 'Settings' },
                ]
              },
            ].map(({ section, items }) => (
              <div key={section}>
                <span className="px-3 text-[10px] text-slate-500 uppercase tracking-widest font-bold block mb-1">{section}</span>
                <ul className="space-y-0.5">
                  {(items as Array<{ id: string; icon: any; label: string; badge?: string; accent?: boolean }>).map(({ id, icon: Icon, label, badge, accent }) => (
                    <li key={id}>
                      <button
                        onClick={() => setActiveNav(id)}
                        className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg transition ${
                          activeNav === id
                            ? 'bg-purple-600/10 text-purple-400 border-l-2 border-purple-500'
                            : 'text-slate-400 hover:text-white hover:bg-slate-800/20'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Icon className={`h-3.5 w-3.5 ${accent ? 'text-purple-400' : ''}`} />
                          <span>{label}</span>
                        </div>
                        {badge && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold">
                            {badge}
                          </span>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </div>

        {/* Plan card */}
        <div className="p-3">
          <div className="p-3 rounded-lg bg-gradient-to-b from-[#1b1c3c] to-[#0d0e23] border border-[#2d2e5a]">
            <span className="text-[10px] text-slate-400 block font-medium">Current Plan</span>
            <span className="text-white font-bold text-sm block">Team Pro</span>
            <div className="mt-1.5 h-1 rounded-full bg-[#1d1e40] overflow-hidden">
              <div className="h-full w-3/4 rounded-full bg-gradient-to-r from-purple-600 to-indigo-500" />
            </div>
            <span className="text-[9px] text-slate-500 block mt-1">3 / 4 workspaces used</span>
          </div>
        </div>
      </aside>

      {/* ══════════════════════════════════════════════════════════════════════
          2. MAIN CONTENT
      ══════════════════════════════════════════════════════════════════════ */}
      <main className="flex-1 flex flex-col h-full bg-[#050816] overflow-y-auto min-w-0">

        {/* Header */}
        <header className="h-14 border-b border-[#152345] px-6 flex items-center justify-between bg-[#04091e]/60 backdrop-blur-md sticky top-0 z-10 shrink-0">
          <div className="flex items-center gap-2 bg-[#0e1633] px-3 py-1.5 rounded-lg border border-[#1d2d5c]">
            <Search className="h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search workspaces…"
              className="bg-transparent border-none outline-none text-slate-200 placeholder-slate-500 w-48"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              id="launch-workspace-btn"
              onClick={() => setShowLaunchModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-medium shadow-md shadow-purple-500/20 transition"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>New Workspace</span>
            </button>
            <button
              onClick={loadData}
              className="p-1.5 rounded-lg bg-[#0e1633] border border-[#1d2d5c] text-slate-400 hover:text-slate-200 transition"
              title="Refresh"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoadingWorkspaces ? 'animate-spin' : ''}`} />
            </button>
            <div className="h-4 w-px bg-[#152345]" />
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white text-[10px] font-bold shadow-md">
                {session?.email?.[0]?.toUpperCase() ?? 'U'}
              </div>
              <span className="text-slate-300 font-semibold text-xs">
                {session?.email ?? 'Demo User'}
              </span>
            </div>
          </div>
        </header>

        <div className="p-6 space-y-6">

          {/* Page title */}
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-bold tracking-widest text-purple-400 block mb-0.5">
                {activeNav === 'overview' ? 'Workspace Overview' : activeNav.charAt(0).toUpperCase() + activeNav.slice(1)}
              </span>
              <h1 className="text-xl font-bold text-white tracking-tight">
                Kubernetes Learning Platform
                {mockMode && (
                  <span className="ml-2 text-xs font-normal text-yellow-500/80 px-2 py-0.5 rounded-full bg-yellow-500/10 border border-yellow-500/20">
                    Mock Mode Active
                  </span>
                )}
              </h1>
            </div>
            <div className="flex items-center gap-6 text-[10px] text-slate-400">
              <div>
                <span className="block text-slate-500 uppercase tracking-wider font-semibold">Running</span>
                <span className="flex items-center gap-1 font-bold text-emerald-400 mt-0.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  {runningCount} workspace{runningCount !== 1 ? 's' : ''}
                </span>
              </div>
              <div className="h-6 w-px bg-[#152345]" />
              <div>
                <span className="block text-slate-500 uppercase tracking-wider font-semibold">Suspended</span>
                <span className="font-bold text-slate-300 mt-0.5 block">{suspendedCount}</span>
              </div>
              <div className="h-6 w-px bg-[#152345]" />
              <div>
                <span className="block text-slate-500 uppercase tracking-wider font-semibold">CPU Active</span>
                <span className="font-bold text-pink-400 mt-0.5 block">{totalCpu} vCPU</span>
              </div>
              <div className="h-6 w-px bg-[#152345]" />
              <div>
                <span className="block text-slate-500 uppercase tracking-wider font-semibold">RAM Active</span>
                <span className="font-bold text-cyan-400 mt-0.5 block">{(totalRam / 1024).toFixed(1)} GB</span>
              </div>
            </div>
          </div>

          {/* Quick metrics */}
          <div className="grid grid-cols-5 gap-4">
            {[
              { label: 'Nodes', value: '12', sub: '8 Ready · 4 Other', icon: Layers, color: 'text-purple-400' },
              { label: 'Pods', value: `${runningCount * 2 + 3}`, sub: `${runningCount * 2} Running`, icon: Layers, color: 'text-indigo-400' },
              { label: 'CPU Usage', value: `${Math.min(99, Math.round(totalCpu * 20))}%`, sub: `${totalCpu} / 5.0 vCPU`, icon: Cpu, color: 'text-pink-400' },
              { label: 'Memory', value: `${Math.min(99, Math.round(totalRam / 409.6))}%`, sub: `${(totalRam / 1024).toFixed(1)} / 39 GB`, icon: Sliders, color: 'text-cyan-400' },
              { label: 'Storage', value: '58%', sub: '580 / 1000 GB', icon: HardDrive, color: 'text-emerald-400' },
            ].map(({ label, value, sub, icon: Icon, color }) => (
              <div key={label} className="p-4 rounded-xl bg-gradient-to-b from-[#0a0f28] to-[#04081c] border border-[#19274c] shadow-lg">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="font-semibold uppercase tracking-wider text-[10px]">{label}</span>
                  <Icon className={`h-4 w-4 ${color}`} />
                </div>
                <span className="text-2xl font-bold text-white tracking-tight">{value}</span>
                <p className="text-[10px] text-slate-500 mt-1">{sub}</p>
              </div>
            ))}
          </div>

          {/* Workspace list */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="font-bold text-slate-300">
                Active Workspaces
                <span className="ml-2 text-[10px] text-slate-500 font-normal">({visibleWorkspaces.length})</span>
              </span>
              <button
                onClick={() => setShowLaunchModal(true)}
                className="flex items-center gap-1 text-[10px] text-purple-400 hover:text-purple-300 transition"
              >
                <Plus className="h-3 w-3" />
                Launch new
              </button>
            </div>

            {isLoadingWorkspaces ? (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="h-6 w-6 animate-spin text-purple-400" />
              </div>
            ) : visibleWorkspaces.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 gap-2 text-slate-500 border border-dashed border-[#152345] rounded-xl">
                <Cloud className="h-8 w-8 opacity-40" />
                <p className="text-sm">No workspaces yet</p>
                <button
                  onClick={() => setShowLaunchModal(true)}
                  className="text-xs text-purple-400 hover:text-purple-300 transition"
                >
                  Launch your first workspace →
                </button>
              </div>
            ) : (
              <AnimatePresence mode="popLayout">
                <div className="grid grid-cols-3 gap-4">
                  {visibleWorkspaces.map((ws) => (
                    <WorkspaceCard
                      key={ws.id}
                      ws={ws}
                      onOpen={() => openSplitView(ws)}
                      onSuspend={() => handleSuspend(ws)}
                      onResume={() => handleResume(ws)}
                      onTerminate={() => handleTerminate(ws)}
                    />
                  ))}
                </div>
              </AnimatePresence>
            )}
          </div>

          {/* Quick actions */}
          <div className="p-4 rounded-xl bg-[#070b21] border border-[#152345]">
            <span className="text-slate-300 font-bold block mb-3">Quick Operational Actions</span>
            <div className="flex gap-3 flex-wrap">
              {[
                { icon: Terminal, label: 'Launch Terminal', color: 'text-purple-400', onClick: () => { const running = workspaces.find(w => w.status === 'running'); if (running) openSplitView(running); } },
                { icon: Code, label: 'Open IDE', color: 'text-indigo-400', onClick: () => { const running = workspaces.find(w => w.status === 'running'); if (running) openSplitView(running); } },
                { icon: Activity, label: 'View Logs', color: 'text-cyan-400', onClick: () => setActiveTab('logs') },
                { icon: Sliders, label: 'Monitor', color: 'text-yellow-400', onClick: () => setActiveTab('metrics') },
                { icon: Shield, label: 'Network Policy', color: 'text-emerald-400', onClick: () => {} },
                { icon: HardDrive, label: 'Create Snapshot', color: 'text-pink-400', onClick: () => {} },
              ].map(({ icon: Icon, label, color, onClick }) => (
                <button
                  key={label}
                  onClick={onClick}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#0e1633] border border-[#20346a] text-slate-200 hover:bg-purple-600 hover:text-white hover:border-purple-500 transition"
                >
                  <Icon className={`h-3.5 w-3.5 ${color}`} />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Terminal / Logs tabs */}
          <div className="rounded-xl bg-[#040819] border border-[#152345] overflow-hidden">
            <div className="flex border-b border-[#152345] px-4 pt-3 pb-0 justify-between items-center">
              <div className="flex gap-4">
                {(['terminal', 'logs', 'events', 'metrics'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`font-semibold pb-2.5 border-b-2 transition capitalize ${
                      activeTab === tab ? 'text-purple-400 border-purple-500' : 'text-slate-500 border-transparent hover:text-slate-300'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
              <div className="flex gap-2 pb-2">
                <button
                  onClick={loadData}
                  className="p-1 rounded bg-[#0e1633] border border-[#1d2d5c] hover:bg-[#14204b] text-slate-400"
                >
                  <RefreshCw className="h-3 w-3" />
                </button>
              </div>
            </div>

            <div className="h-56">
              {activeTab === 'terminal' ? (
                <XtermTerminal className="h-full rounded-none border-none" />
              ) : (
                <div className="h-full bg-[#010410] border border-[#111c3a] p-3 font-mono text-[10px] overflow-y-auto leading-relaxed">
                  {activeTab === 'logs' && (
                    <div className="space-y-0.5 text-slate-400">
                      <div>[2026-05-21 05:00:00] <span className="text-blue-400">[INFO]</span> API server started on port 8000</div>
                      <div>[2026-05-21 05:00:05] <span className="text-blue-400">[INFO]</span> Database connection pool initialized (10 connections)</div>
                      <div>[2026-05-21 05:00:10] <span className="text-yellow-400">[WARN]</span> Celery beat idle-detection task scheduled every 5m</div>
                      <div>[2026-05-21 05:00:30] <span className="text-red-400">[ERROR]</span> Worker pod CrashLoopBackOff — DB connection timeout</div>
                      <div>[2026-05-21 05:01:00] <span className="text-blue-400">[INFO]</span> Workspace a1b2c3d4 status → running</div>
                    </div>
                  )}
                  {activeTab === 'events' && (
                    <div className="text-indigo-300 space-y-1">
                      <div className="text-slate-500">LAST SEEN   TYPE      REASON             OBJECT                           MESSAGE</div>
                      <div>2m          <span className="text-yellow-400">Warning</span>   FailedScheduling   pod/frontend-7f8d-abcde          0/12 nodes available: quota exceeded</div>
                      <div>1m          <span className="text-emerald-400">Normal</span>    Scheduled          pod/worker-7f9c-ptulo             Successfully assigned to node-3</div>
                      <div>30s         <span className="text-yellow-400">Warning</span>   BackOff            pod/worker-7f9c-ptulo             Back-off restarting failed container</div>
                    </div>
                  )}
                  {activeTab === 'metrics' && (
                    <div className="text-cyan-300 space-y-1">
                      <div className="text-slate-400">SCRAPING PROMETHEUS TARGETS [ACTIVE] · interval=15s</div>
                      <div>node_cpu_seconds_total&#123;mode="idle"&#125; {(Math.random() * 10000 + 20000).toFixed(2)}</div>
                      <div>node_memory_Active_bytes {(Math.random() * 1e9 + 2e10).toFixed(0)}</div>
                      <div>container_network_receive_bytes_total {(Math.random() * 1e8 + 9e7).toFixed(0)} bytes</div>
                      <div>kube_pod_status_phase&#123;phase="Running"&#125; {runningCount * 2}</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* ══════════════════════════════════════════════════════════════════════
          3. RIGHT AI SIDEBAR
      ══════════════════════════════════════════════════════════════════════ */}
      <aside className="w-80 bg-[#04091e] border-l border-[#152345] flex flex-col h-full shrink-0">

        {/* Header */}
        <div className="p-4 border-b border-[#152345] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-md shadow-purple-500/20">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div>
              <span className="font-bold text-slate-200 block text-sm">AI Assistant</span>
              <span className="text-[9px] text-slate-500">Powered by {mockMode ? 'Mock Engine' : 'Ollama / OpenAI'}</span>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-[#111e3b] border border-[#213560] text-purple-300 font-semibold uppercase tracking-wider">
              {mockMode ? 'Sandbox' : 'Hybrid'}
            </span>
          </div>
        </div>

        {/* Messages */}
        <div ref={aiScrollRef} className="flex-1 p-4 overflow-y-auto space-y-3 min-h-0">
          <AnimatePresence initial={false}>
            {aiMessages.map((msg) => (
              <motion.div
                key={msg.ts}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`p-3 rounded-xl max-w-[92%] leading-relaxed text-[11px] whitespace-pre-line ${
                    msg.sender === 'user'
                      ? 'bg-purple-600 text-white rounded-br-sm shadow-lg shadow-purple-900/30'
                      : 'bg-[#0f1532] border border-[#1b2b5a] text-slate-200 rounded-bl-sm'
                  }`}
                >
                  {msg.text}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {aiLoading && (
            <div className="flex justify-start">
              <div className="p-3 rounded-xl bg-[#0f1532] border border-[#1b2b5a] flex items-center gap-2">
                <Loader2 className="h-3 w-3 animate-spin text-purple-400" />
                <span className="text-[10px] text-slate-400">Analyzing…</span>
              </div>
            </div>
          )}
        </div>

        {/* Quick suggestions */}
        <div className="px-4 space-y-1.5 shrink-0">
          <span className="text-[9px] text-slate-500 uppercase tracking-widest font-bold block">Quick Prompts</span>
          {[
            'Why is my worker pod crashing?',
            'Show CPU usage statistics',
            "Explain 'CrashLoopBackOff'",
          ].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => handleSuggestion(suggestion)}
              className="w-full flex items-center justify-between p-2 rounded-lg bg-[#070b21] hover:bg-[#0c143a] border border-[#14234b] text-left transition"
            >
              <span className="text-slate-300 text-[11px]">{suggestion}</span>
              <ChevronRight className="h-3 w-3 text-slate-600 shrink-0" />
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-[#152345] shrink-0">
          <form
            onSubmit={(e) => { e.preventDefault(); handleSendAi(aiInput); }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={aiInput}
              onChange={(e) => setAiInput(e.target.value)}
              placeholder="Ask anything or paste logs…"
              className="flex-1 bg-[#070b21] border border-[#1d2d5c] rounded-lg px-3 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/20 text-xs"
            />
            <button
              type="submit"
              disabled={aiLoading || !aiInput.trim()}
              className="p-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white shadow-lg transition"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
          <div className="mt-2 text-[9px] text-slate-600 flex items-center justify-between">
            <span>
              Context: {runningCount} running · {suspendedCount} suspended
            </span>
            <button
              onClick={() => store.clearAiMessages()}
              className="text-slate-600 hover:text-slate-400 transition"
            >
              Clear
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
