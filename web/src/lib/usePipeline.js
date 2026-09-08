import { useCallback, useEffect, useRef, useState } from 'react';
import { executeTask, approveAndRun, rejectTask, logSocketUrl } from './api';
import { newRunContext, parseLogLine } from './logParser';
import { timeNow } from './roles';

function colorFor(line) {
  if (/FAILED|ERROR|Traceback/i.test(line)) return '#ff8a80';
  if (/SUCCESS| OK |healthy/i.test(line)) return '#7ee787';
  if (/self-heal|SELF-HEAL/i.test(line)) return '#e0b341';
  return 'var(--dim3)';
}

const initialState = {
  phase: 'idle',
  running: false,
  task: '',
  logs: [],
  termLines: [{ text: '$ made — waiting for a task…', c: 'var(--dim3)' }],
  code: '',
  priorCode: null,
  healError: null,
  selfHealed: false,
  healAttempts: 0,
  failureClass: null,
  reviewerReport: '',
  securityAudit: null,       // { verdict, findings:[…] } from graph.reviewer_node
  researchSources: [],       // [{ title, snippet }] from graph.researcher_node
  subprocessResult: null,
  errorMessage: null,
};

// Drives the whole Session view off the *real* FastAPI backend: dispatches a task,
// infers live pipeline phase by parsing the /ws/logs stream while /execute-task is
// in flight (that endpoint blocks until the whole graph — self-heal loop included —
// finishes and only then resolves once), then hands off to /approve-and-run or
// /reject-task for the HITL gate.
export function usePipeline() {
  const [state, setState] = useState(initialState);
  const codeRef = useRef('');
  const runningRef = useRef(false);
  const runCtxRef = useRef(newRunContext());

  useEffect(() => { codeRef.current = state.code; }, [state.code]);
  useEffect(() => { runningRef.current = state.running; }, [state.running]);

  useEffect(() => {
    let cancelled = false;
    let ws;
    let retryTimer;
    function connect() {
      ws = new WebSocket(logSocketUrl());
      ws.onmessage = (evt) => {
        const line = evt.data;
        setState((s) => ({ ...s, termLines: [...s.termLines, { text: line, c: colorFor(line) }].slice(-500) }));
        if (!runningRef.current) return;
        const parsed = parseLogLine(line, runCtxRef.current);
        if (parsed) {
          setState((s) => ({
            ...s,
            phase: parsed.phase,
            logs: [...s.logs, { role: parsed.role, time: timeNow(), text: parsed.text }],
          }));
        }
      };
      ws.onclose = () => { if (!cancelled) retryTimer = setTimeout(connect, 3000); };
      ws.onerror = () => ws.close();
    }
    connect();
    return () => {
      cancelled = true;
      clearTimeout(retryTimer);
      if (ws) ws.close();
    };
  }, []);

  const dispatch = useCallback(async (taskText) => {
    const text = (taskText || '').trim();
    if (!text || runningRef.current) return;
    runCtxRef.current = newRunContext();
    setState((s) => ({
      ...s,
      running: true,
      phase: 'researching',
      task: text,
      logs: [...s.logs, { role: 'Operator', time: timeNow(), text }],
      code: '',
      priorCode: null,
      healError: null,
      selfHealed: false,
      healAttempts: 0,
      failureClass: null,
      reviewerReport: '',
      securityAudit: null,
      researchSources: [],
      subprocessResult: null,
      errorMessage: null,
    }));
    try {
      const data = await executeTask(text);
      // The graph terminated without a HITL handoff — either the AST audit
      // blocked the code or self-heal exhausted its retry cap.
      const terminal = data.failure_class && data.failure_class !== 'none';
      const reviewerNote = terminal
        ? `Pipeline terminated (${data.failure_class}). See the security audit strip for details.`
        : 'Constraints checked. Awaiting human authorization to run against the workspace.';
      setState((s) => ({
        ...s,
        running: false,
        phase: terminal ? (data.failure_class === 'policy' ? 'blocked' : 'exhausted') : 'awaiting_hitl',
        code: data.proposed_code || '',
        priorCode: data.prior_code || null,
        healError: data.heal_error || null,
        selfHealed: !!data.self_healed,
        healAttempts: data.heal_attempts || 0,
        failureClass: data.failure_class || null,
        reviewerReport: data.reviewer_security_report || '',
        securityAudit: data.security_audit || null,
        researchSources: data.research_sources || [],
        logs: [
          ...s.logs,
          ...(data.research_sources && data.research_sources.length
            ? [{ role: 'Researcher', time: timeNow(), text: `Grounded in ${data.research_sources.length} FAISS methodology docs: ${data.research_sources.map((r) => r.title).join(' · ')}` }]
            : []),
          { role: 'Reviewer', time: timeNow(), text: reviewerNote },
        ],
      }));
    } catch (err) {
      setState((s) => ({ ...s, running: false, phase: 'error', errorMessage: err.message }));
    }
  }, []);

  const approve = useCallback(async () => {
    setState((s) => ({ ...s, phase: 'running_subprocess' }));
    try {
      const result = await approveAndRun(codeRef.current);
      const ok = result.status === 'Execution Successful';
      setState((s) => ({
        ...s,
        phase: ok ? 'complete' : 'error',
        subprocessResult: result,
        logs: [...s.logs, {
          role: 'Subprocess',
          time: timeNow(),
          text: ok
            ? `Execution successful.\n${result.stdout || ''}`.trim()
            : `Execution failed.\n${result.stderr || result.status || ''}`.trim(),
        }],
      }));
    } catch (err) {
      setState((s) => ({ ...s, phase: 'error', errorMessage: err.message }));
    }
  }, []);

  const reject = useCallback(async () => {
    setState((s) => ({
      ...s,
      phase: 'rejected',
      code: '',
      logs: [...s.logs, { role: 'Operator', time: timeNow(), text: 'Pipeline rejected by human-in-the-loop. Session cleared.' }],
    }));
    try {
      await rejectTask();
    } catch (err) {
      // cleanup failing on the backend shouldn't block the UI from resetting
      console.error('reject-task failed', err);
    }
  }, []);

  const reset = useCallback(() => {
    setState((s) => ({ ...initialState, termLines: s.termLines }));
  }, []);

  return { state, dispatch, approve, reject, reset };
}
