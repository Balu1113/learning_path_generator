import { useSyncExternalStore } from "react";
import { logFocus } from "./api/client";

export const WORK_OPTIONS = [15, 25, 50];
export const BREAK_MIN = 5;

let state = {
  mode: "work",
  workMin: 25,
  running: false,
  endsAt: null,
  remaining: 25 * 60,
  ctx: null,
  note: null,
};

const listeners = new Set();

function emit() {
  for (const l of listeners) l();
}

function set(patch) {
  state = { ...state, ...patch };
  emit();
}

function fullFor(s) {
  return (s.mode === "work" ? s.workMin : BREAK_MIN) * 60;
}

function currentRemaining() {
  if (state.running && state.endsAt) {
    return Math.max(0, Math.ceil((state.endsAt - Date.now()) / 1000));
  }
  return state.remaining;
}

function sameCtx(a, b) {
  if (a === b) return true;
  if (!a || !b) return false;
  return a.pathId === b.pathId && a.phaseIdx === b.phaseIdx
    && a.canLog === b.canLog && a.phaseTitle === b.phaseTitle;
}

export function hoursLabel(sec) {
  const s = Math.max(0, sec);
  if (s < 60) return `${s}s`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

export function clockLabel(sec) {
  const s = Math.max(0, sec);
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

async function doLog(secs, { resetAfter = false } = {}) {
  const ctx = state.ctx;
  if (!ctx || !ctx.pathId || !ctx.canLog) {
    set({ note: { kind: "ok", text: "Session complete — sign in to save focus time." } });
    return;
  }
  try {
    const d = await logFocus({
      path_id: ctx.pathId,
      phase_idx: ctx.phaseIdx > 0 ? ctx.phaseIdx : 0,
      phase_title: ctx.phaseTitle || "",
      seconds: secs,
    });
    if (d.error) {
      set({ note: { kind: "err", text: d.error } });
      return;
    }
    const patch = { note: { kind: "ok", text: `Logged ${hoursLabel(secs)} focus session.` } };
    if (resetAfter) {
      patch.running = false;
      patch.endsAt = null;
      patch.remaining = fullFor(state);
    }
    set(patch);
  } catch {
    set({ note: { kind: "err", text: "Could not save the focus session." } });
  }
}

function finishSegment() {
  if (state.mode === "work") {
    const secs = state.workMin * 60;
    set({ running: false, endsAt: null, mode: "break", remaining: BREAK_MIN * 60 });
    doLog(secs);
  } else {
    set({ running: false, endsAt: null, mode: "work", remaining: state.workMin * 60 });
  }
}

function tick() {
  if (!state.running || !state.endsAt) return;
  const remaining = Math.max(0, Math.ceil((state.endsAt - Date.now()) / 1000));
  if (remaining === state.remaining) return;
  if (remaining === 0) {
    finishSegment();
    return;
  }
  set({ remaining });
}

if (typeof window !== "undefined" && !globalThis.__pomodoroTick) {
  globalThis.__pomodoroTick = setInterval(tick, 500);
}

export function subscribePomodoro(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getPomodoroState() {
  return state;
}

export const pomodoroActions = {
  setCtx(ctx) {
    if (sameCtx(state.ctx, ctx)) return;
    set({ ctx });
  },
  toggleRun() {
    if (state.running) {
      set({ running: false, endsAt: null, remaining: currentRemaining() });
    } else {
      const remaining = state.remaining > 0 ? state.remaining : fullFor(state);
      set({ running: true, endsAt: Date.now() + remaining * 1000, remaining });
    }
  },
  reset() {
    set({ running: false, endsAt: null, remaining: fullFor(state) });
  },
  setMode(mode) {
    set({
      mode,
      running: false,
      endsAt: null,
      remaining: (mode === "work" ? state.workMin : BREAK_MIN) * 60,
    });
  },
  setWorkMin(workMin) {
    set({ workMin, mode: "work", running: false, endsAt: null, remaining: workMin * 60 });
  },
  async logNow() {
    if (state.mode !== "work") return;
    const secs = state.workMin * 60 - currentRemaining();
    if (secs < 30) return;
    await doLog(secs, { resetAfter: true });
  },
};

export function usePomodoro() {
  const snap = useSyncExternalStore(subscribePomodoro, getPomodoroState, getPomodoroState);
  return { ...snap, ...pomodoroActions };
}
