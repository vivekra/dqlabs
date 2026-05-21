'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Wifi, WifiOff, RefreshCw, Loader2, Maximize2, Copy, Check } from 'lucide-react';

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

interface XtermTerminalProps {
  /** Full wss:// URL including ?token= and &tenant_id= query params */
  wsUrl?: string;
  /** Fallback mock lines when no wsUrl is provided */
  mockLines?: string[];
  className?: string;
  onConnectionChange?: (state: ConnectionState) => void;
}

const MOCK_BOOT_SEQUENCE = [
  '\x1b[1;32m██████╗ ██╗ ██████╗ ██╗████████╗ █████╗ ██╗      ██████╗ \x1b[0m',
  '\x1b[1;32m██╔══██╗██║██╔════╝ ██║╚══██╔══╝██╔══██╗██║     ██╔═══██╗\x1b[0m',
  '\x1b[1;35m██║  ██║██║██║  ███╗██║   ██║   ███████║██║     ██║   ██║\x1b[0m',
  '\x1b[1;35m██║  ██║██║██║   ██║██║   ██║   ██╔══██║██║     ██║▄▄ ██║\x1b[0m',
  '\x1b[1;36m██████╔╝██║╚██████╔╝██║   ██║   ██║  ██║███████╗╚██████╔╝\x1b[0m',
  '\x1b[1;36m╚═════╝ ╚═╝ ╚═════╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝ ╚══▀▀═╝ \x1b[0m',
  '',
  '\x1b[90m──────────────────────────────────────────────────────────────\x1b[0m',
  '\x1b[36m  DigitalQ Labs  •  AI-Native Kubernetes Workspace Engine\x1b[0m',
  '\x1b[90m──────────────────────────────────────────────────────────────\x1b[0m',
  '',
  '\x1b[33m[MOCK MODE]\x1b[0m \x1b[90mNo live cluster connected. Terminal running in sandbox.\x1b[0m',
  '',
  '\x1b[1;37muser@digitalqlabs\x1b[0m:\x1b[34m~/workspace\x1b[0m$ \x1b[32mkubectl get pods -A\x1b[0m',
  'NAMESPACE     NAME                               READY   STATUS              RESTARTS   AGE',
  'frontend      frontend-7f8d9c4d8-abcde           \x1b[32m1/1\x1b[0m     \x1b[32mRunning\x1b[0m             0          2d',
  'frontend      frontend-7f8d9c4d8-fghij           \x1b[32m1/1\x1b[0m     \x1b[32mRunning\x1b[0m             1          2d',
  'backend       backend-api-6c5d7f9b-xyz12         \x1b[32m1/1\x1b[0m     \x1b[32mRunning\x1b[0m             0          2d',
  'backend       worker-7f9c8d7f6-ptulo             \x1b[31m0/1\x1b[0m     \x1b[31mCrashLoopBackOff\x1b[0m    7          1d',
  'data          postgres-0                         \x1b[32m1/1\x1b[0m     \x1b[32mRunning\x1b[0m             0          5d',
  'data          redis-master-0                     \x1b[32m1/1\x1b[0m     \x1b[32mRunning\x1b[0m             0          5d',
  '',
  '\x1b[1;37muser@digitalqlabs\x1b[0m:\x1b[34m~/workspace\x1b[0m$ \x1b[0m',
];

const CONNECTION_COLORS: Record<ConnectionState, string> = {
  disconnected: 'text-slate-500',
  connecting: 'text-yellow-400',
  connected: 'text-emerald-400',
  reconnecting: 'text-orange-400',
  error: 'text-red-400',
};

const CONNECTION_LABELS: Record<ConnectionState, string> = {
  disconnected: 'Disconnected',
  connecting: 'Connecting…',
  connected: 'Live',
  reconnecting: 'Reconnecting…',
  error: 'Connection Error',
};

export default function XtermTerminal({
  wsUrl,
  mockLines,
  className = '',
  onConnectionChange,
}: XtermTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<import('xterm').Terminal | null>(null);
  const fitAddonRef = useRef<import('xterm-addon-fit').FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECTS = 5;

  const [connState, setConnState] = useState<ConnectionState>('disconnected');
  const [copied, setCopied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const isMockMode = !wsUrl;

  const updateConnState = useCallback(
    (s: ConnectionState) => {
      setConnState(s);
      onConnectionChange?.(s);
    },
    [onConnectionChange]
  );

  // ── Bootstrap xterm.js (dynamic import to avoid SSR) ───────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    let term: import('xterm').Terminal;
    let fitAddon: import('xterm-addon-fit').FitAddon;

    (async () => {
      const { Terminal } = await import('xterm');
      const { FitAddon } = await import('xterm-addon-fit');

      term = new Terminal({
        theme: {
          background: '#010410',
          foreground: '#e2e8f0',
          cursor: '#a855f7',
          cursorAccent: '#0f0f1a',
          selectionBackground: '#4f46e5aa',
          black: '#0f172a',
          red: '#f87171',
          green: '#4ade80',
          yellow: '#facc15',
          blue: '#60a5fa',
          magenta: '#c084fc',
          cyan: '#67e8f9',
          white: '#e2e8f0',
          brightBlack: '#334155',
          brightRed: '#fca5a5',
          brightGreen: '#86efac',
          brightYellow: '#fde047',
          brightBlue: '#93c5fd',
          brightMagenta: '#d8b4fe',
          brightCyan: '#a5f3fc',
          brightWhite: '#f8fafc',
        },
        fontFamily: '"Cascadia Code", "JetBrains Mono", "Fira Code", monospace',
        fontSize: 12,
        lineHeight: 1.45,
        cursorBlink: true,
        cursorStyle: 'underline',
        scrollback: 5000,
        allowTransparency: true,
        convertEol: true,
      });

      fitAddon = new FitAddon();
      term.loadAddon(fitAddon);
      term.open(containerRef.current!);
      fitAddon.fit();

      termRef.current = term;
      fitAddonRef.current = fitAddon;

      if (isMockMode) {
        // Print mock content with animation
        const lines = mockLines ?? MOCK_BOOT_SEQUENCE;
        for (const line of lines) {
          term.writeln(line);
          await new Promise((r) => setTimeout(r, 18));
        }
        // Interactive mock input
        let mockInput = '';
        term.onKey(({ key, domEvent }) => {
          if (domEvent.keyCode === 13) {
            term.writeln('');
            const trimmed = mockInput.trim();
            if (trimmed === 'clear') {
              term.clear();
            } else if (trimmed) {
              term.writeln(
                `\x1b[90mbash: ${trimmed}: command not found (mock mode)\x1b[0m`
              );
            }
            mockInput = '';
            term.write('\x1b[1;37muser@digitalqlabs\x1b[0m:\x1b[34m~/workspace\x1b[0m$ ');
          } else if (domEvent.keyCode === 8) {
            if (mockInput.length > 0) {
              mockInput = mockInput.slice(0, -1);
              term.write('\b \b');
            }
          } else if (key.length === 1) {
            mockInput += key;
            term.write(key);
          }
        });
      }
    })();

    const resizeObserver = new ResizeObserver(() => {
      fitAddonRef.current?.fit();
    });
    if (containerRef.current) resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      termRef.current?.dispose();
      termRef.current = null;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMockMode]);

  // ── WebSocket connection for live terminal ──────────────────────────────────
  const connect = useCallback(() => {
    if (!wsUrl || !termRef.current) return;

    updateConnState('connecting');
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      updateConnState('connected');
      termRef.current?.writeln('\x1b[32m✓ Connected to workspace terminal\x1b[0m');
      termRef.current?.writeln('');
      fitAddonRef.current?.fit();
    };

    ws.onmessage = (event) => {
      const data = typeof event.data === 'string' ? event.data : '';
      termRef.current?.write(data);
    };

    ws.onclose = (e) => {
      if (e.code === 1000) {
        updateConnState('disconnected');
        return;
      }
      const attempts = ++reconnectAttemptsRef.current;
      if (attempts <= MAX_RECONNECTS) {
        updateConnState('reconnecting');
        termRef.current?.writeln(
          `\r\n\x1b[33m⚡ Connection lost. Reconnecting (${attempts}/${MAX_RECONNECTS})…\x1b[0m`
        );
        const delay = Math.min(1000 * 2 ** attempts, 30000);
        reconnectTimerRef.current = setTimeout(connect, delay);
      } else {
        updateConnState('error');
        termRef.current?.writeln('\r\n\x1b[31m✗ Max reconnect attempts reached.\x1b[0m');
      }
    };

    ws.onerror = () => {
      updateConnState('error');
    };

    // Forward keyboard input to WebSocket
    termRef.current.onKey(({ key }) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(key);
    });
  }, [wsUrl, updateConnState]);

  useEffect(() => {
    if (wsUrl) {
      // Small delay to ensure xterm is initialised first
      const t = setTimeout(connect, 400);
      return () => clearTimeout(t);
    }
  }, [wsUrl, connect]);

  const handleCopySession = async () => {
    const content = termRef.current?.getSelection() ?? '';
    if (content) {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const handleReconnect = () => {
    reconnectAttemptsRef.current = 0;
    wsRef.current?.close();
    connect();
  };

  return (
    <div
      className={`flex flex-col h-full rounded-xl overflow-hidden border border-[#152345] bg-[#010410] ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none' : ''
      } ${className}`}
    >
      {/* Terminal header bar */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#04091e] border-b border-[#152345] shrink-0">
        <div className="flex items-center gap-2">
          <Terminal className="h-3.5 w-3.5 text-purple-400" />
          <span className="text-xs font-semibold text-slate-300 tracking-wide">
            {isMockMode ? 'Sandbox Terminal' : 'Workspace Terminal'}
          </span>
          {isMockMode && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 font-semibold uppercase tracking-wider">
              Mock
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Connection status indicator */}
          <AnimatePresence mode="wait">
            <motion.div
              key={connState}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              className={`flex items-center gap-1.5 text-[10px] font-semibold ${CONNECTION_COLORS[connState]}`}
            >
              {connState === 'connected' ? (
                <Wifi className="h-3 w-3" />
              ) : connState === 'connecting' || connState === 'reconnecting' ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <WifiOff className="h-3 w-3" />
              )}
              <span>{CONNECTION_LABELS[connState]}</span>
              {connState === 'connected' && (
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              )}
            </motion.div>
          </AnimatePresence>

          <div className="h-3 w-px bg-slate-700" />

          {/* Copy button */}
          <button
            onClick={handleCopySession}
            className="p-1 rounded hover:bg-slate-800 transition text-slate-500 hover:text-slate-200"
            title="Copy selection"
          >
            {copied ? (
              <Check className="h-3 w-3 text-emerald-400" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
          </button>

          {/* Reconnect button (live mode only) */}
          {!isMockMode && (
            <button
              onClick={handleReconnect}
              className="p-1 rounded hover:bg-slate-800 transition text-slate-500 hover:text-slate-200"
              title="Reconnect"
            >
              <RefreshCw className="h-3 w-3" />
            </button>
          )}

          {/* Fullscreen toggle */}
          <button
            onClick={() => setIsFullscreen((v) => !v)}
            className="p-1 rounded hover:bg-slate-800 transition text-slate-500 hover:text-slate-200"
            title="Toggle fullscreen"
          >
            <Maximize2 className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* xterm.js mount point */}
      <div ref={containerRef} className="flex-1 min-h-0 p-1" />
    </div>
  );
}
