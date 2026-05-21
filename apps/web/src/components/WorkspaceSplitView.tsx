'use client';

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import {
  Code,
  Terminal,
  X,
  GripVertical,
  ExternalLink,
  RefreshCw,
  Loader2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { Workspace } from '../store/workspaceStore';
import { buildTerminalWsUrl } from '../lib/api';

// Dynamically import xterm to avoid SSR
const XtermTerminal = dynamic(() => import('./XtermTerminal'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center bg-[#010410]">
      <div className="flex items-center gap-2 text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-xs">Loading terminal…</span>
      </div>
    </div>
  ),
});

type PaneMode = 'split' | 'ide-only' | 'terminal-only';

interface WorkspaceSplitViewProps {
  workspace: Workspace;
  token?: string;
  onClose: () => void;
}

export default function WorkspaceSplitView({
  workspace,
  token = '',
  onClose,
}: WorkspaceSplitViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const dividerRef = useRef<HTMLDivElement>(null);

  const [paneMode, setPaneMode] = useState<PaneMode>('split');
  const [splitRatio, setSplitRatio] = useState(0.55); // IDE takes 55% by default
  const [isDragging, setIsDragging] = useState(false);
  const [iframeKey, setIframeKey] = useState(0); // Force iframe reload
  const [iframeLoading, setIframeLoading] = useState(true);

  const isRunning = workspace.status === 'running';
  const ideUrl = workspace.ingress_url ?? '';
  const wsUrl =
    isRunning && token ? buildTerminalWsUrl(workspace, token) : undefined;

  // ── Drag-to-resize divider ────────────────────────────────────────────────
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);

    const startX = e.clientX;
    const container = containerRef.current;
    if (!container) return;
    const totalWidth = container.getBoundingClientRect().width;
    const startRatio = splitRatio;

    const onMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - startX;
      const newRatio = Math.min(0.8, Math.max(0.2, startRatio + delta / totalWidth));
      setSplitRatio(newRatio);
    };

    const onMouseUp = () => {
      setIsDragging(false);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }, [splitRatio]);

  // Prevent text selection while dragging
  useEffect(() => {
    if (isDragging) {
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'col-resize';
    } else {
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    }
  }, [isDragging]);

  const ideWidthPercent = paneMode === 'ide-only' ? 100 : paneMode === 'terminal-only' ? 0 : splitRatio * 100;
  const termWidthPercent = 100 - ideWidthPercent;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="fixed inset-0 z-40 flex flex-col bg-[#02050f]"
    >
      {/* ── Top bar ──────────────────────────────────────────────────────────── */}
      <header className="h-11 flex items-center justify-between px-4 border-b border-[#152345] bg-[#04091e] shrink-0">
        <div className="flex items-center gap-3">
          {/* Traffic-light dots */}
          <button
            onClick={onClose}
            className="h-3.5 w-3.5 rounded-full bg-red-500 hover:bg-red-400 transition shadow-lg shadow-red-500/30"
            title="Close workspace"
          />
          <div className="h-3.5 w-3.5 rounded-full bg-yellow-500 shadow-lg shadow-yellow-500/20" />
          <div className="h-3.5 w-3.5 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/20" />

          <div className="h-4 w-px bg-slate-700 mx-1" />

          <span className="text-xs font-semibold text-slate-300">{workspace.name}</span>
          <span
            className={`text-[9px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider border ${
              isRunning
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
            }`}
          >
            {workspace.status}
          </span>
        </div>

        {/* Pane mode switcher */}
        <div className="flex items-center gap-1 bg-[#0a0f28] rounded-lg p-1 border border-[#1d2d5c]">
          <button
            onClick={() => setPaneMode('ide-only')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold transition ${
              paneMode === 'ide-only'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Code className="h-3 w-3" />
            IDE
          </button>
          <button
            onClick={() => setPaneMode('split')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold transition ${
              paneMode === 'split'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <GripVertical className="h-3 w-3" />
            Split
          </button>
          <button
            onClick={() => setPaneMode('terminal-only')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold transition ${
              paneMode === 'terminal-only'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Terminal className="h-3 w-3" />
            Terminal
          </button>
        </div>

        <div className="flex items-center gap-2">
          {ideUrl && (
            <a
              href={ideUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-white transition"
            >
              <ExternalLink className="h-3 w-3" />
              Open in tab
            </a>
          )}
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-slate-800 transition text-slate-500 hover:text-slate-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* ── Main pane area ────────────────────────────────────────────────────── */}
      <div ref={containerRef} className="flex flex-1 min-h-0 overflow-hidden">

        {/* IDE Pane */}
        <AnimatePresence>
          {paneMode !== 'terminal-only' && (
            <motion.div
              initial={{ width: '55%' }}
              animate={{ width: `${ideWidthPercent}%` }}
              exit={{ width: 0 }}
              transition={{ duration: isDragging ? 0 : 0.2 }}
              className="flex flex-col h-full border-r border-[#152345] overflow-hidden shrink-0"
              style={{ width: `${ideWidthPercent}%` }}
            >
              {/* IDE pane header */}
              <div className="flex items-center justify-between px-3 py-1.5 bg-[#04091e] border-b border-[#152345] shrink-0">
                <div className="flex items-center gap-2">
                  <Code className="h-3 w-3 text-indigo-400" />
                  <span className="text-[10px] font-semibold text-slate-400">VS Code · code-server</span>
                </div>
                <div className="flex items-center gap-1.5">
                  {isRunning && (
                    <button
                      onClick={() => { setIframeKey(k => k + 1); setIframeLoading(true); }}
                      className="p-0.5 rounded hover:bg-slate-800 transition text-slate-600 hover:text-slate-300"
                      title="Reload IDE"
                    >
                      <RefreshCw className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </div>

              {/* IDE content */}
              <div className="flex-1 relative bg-[#0d0e23]">
                {!isRunning ? (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-500">
                    <AlertTriangle className="h-8 w-8 text-yellow-600/60" />
                    <p className="text-sm font-medium text-slate-400">Workspace not running</p>
                    <p className="text-xs text-slate-600 text-center max-w-xs">
                      Resume or launch this workspace to open the browser IDE.
                    </p>
                  </div>
                ) : (
                  <>
                    {iframeLoading && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-10 bg-[#0d0e23]">
                        <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
                        <p className="text-xs text-slate-500">Loading VS Code…</p>
                      </div>
                    )}
                    <iframe
                      key={iframeKey}
                      src={ideUrl}
                      className="w-full h-full border-none"
                      sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-pointer-lock"
                      title="VS Code IDE"
                      onLoad={() => setIframeLoading(false)}
                    />
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Resize Divider */}
        {paneMode === 'split' && (
          <div
            ref={dividerRef}
            onMouseDown={onMouseDown}
            className={`relative flex items-center justify-center w-1 shrink-0 cursor-col-resize group transition-colors ${
              isDragging ? 'bg-purple-500/50' : 'bg-[#152345] hover:bg-purple-500/40'
            }`}
          >
            <div className="flex flex-col gap-0.5 opacity-60 group-hover:opacity-100 transition-opacity">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-1 w-1 rounded-full bg-slate-400" />
              ))}
            </div>
          </div>
        )}

        {/* Terminal Pane */}
        <AnimatePresence>
          {paneMode !== 'ide-only' && (
            <motion.div
              animate={{ width: `${termWidthPercent}%` }}
              transition={{ duration: isDragging ? 0 : 0.2 }}
              className="flex flex-col h-full min-w-0 flex-1 overflow-hidden"
              style={{ width: `${termWidthPercent}%` }}
            >
              <XtermTerminal
                wsUrl={wsUrl}
                className="flex-1 h-full rounded-none border-none"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Status bar ───────────────────────────────────────────────────────── */}
      <footer className="h-6 flex items-center justify-between px-4 bg-[#02050f] border-t border-[#0a1020] text-[9px] text-slate-600 shrink-0">
        <div className="flex items-center gap-4">
          <span>Namespace: <span className="text-slate-400">{workspace.namespace ?? '—'}</span></span>
          <span>CPU: <span className="text-slate-400">{workspace.allocated_cpu} vCPU</span></span>
          <span>RAM: <span className="text-slate-400">{(workspace.allocated_ram_mb / 1024).toFixed(1)} GB</span></span>
          <span>Storage: <span className="text-slate-400">{workspace.allocated_storage_gb} GB</span></span>
        </div>
        <div className="flex items-center gap-4">
          {workspace.ingress_url && (
            <span className="text-slate-500 truncate max-w-xs">{workspace.ingress_url}</span>
          )}
          <span>DigitalQ Labs · AI Workspace Engine</span>
        </div>
      </footer>
    </motion.div>
  );
}
