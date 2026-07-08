/**
 * Iter 79j.63 — Local ErrorBoundary for the ProfileAnnotator modal.
 *
 * The Jul 7 2026 EST-910869 incident: a `TypeError: Cannot read
 * properties of undefined (reading 'toFixed')` inside ProfileAnnotator
 * unmounted the ENTIRE React tree — every button on the page went
 * inert, the browser dev-tools overlay swallowed keyboard input, and
 * the annotator's "invisible annotations" symptom was really the
 * whole app being frozen at a crash screen.
 *
 * A local ErrorBoundary around the annotator contains the blast
 * radius: the annotator itself unmounts and shows a recoverable
 * fallback, but the surrounding estimate editor + main modal + all
 * other buttons keep working. The contractor can close the annotator,
 * reload, and continue quoting.
 *
 * We DO NOT catch here — the primary fix is the `normalizeScaleRef`
 * helper in ProfileAnnotator.jsx that eliminates the actual crash.
 * This boundary is defensive scaffolding for the next unforeseen
 * runtime error inside the annotator (and only the annotator).
 */
import React from "react";
import { AlertTriangle } from "lucide-react";

export default class AnnotatorErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Structured console log — dev tools can inspect, prod errors
    // land in the browser's error log.
    console.error("[AnnotatorErrorBoundary] annotator crashed:", error, info);
  }

  handleReset = () => {
    // Re-mount the annotator by clearing the error state. The child
    // will be re-created from scratch on the next render.
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) this.props.onReset();
  };

  handleClose = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onClose) this.props.onClose();
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }
    const msg = String(this.state.error?.message || this.state.error || "Unknown error");
    return (
      <div
        className="fixed inset-0 z-[9999] bg-black/50 flex items-center justify-center p-4"
        data-testid="annotator-error-boundary"
      >
        <div className="bg-[var(--surface)] border-2 border-[var(--danger)] max-w-md w-full p-6">
          <div className="flex items-start gap-3 mb-3">
            <AlertTriangle className="w-6 h-6 text-[var(--danger-text)] flex-shrink-0 mt-0.5" />
            <div>
              <div className="text-xs uppercase tracking-wider font-bold text-[var(--danger-text)] mb-1">
                Annotator crashed — session preserved
              </div>
              <div className="text-sm text-[var(--ink)]">
                A rendering error stopped the profile annotator, but{" "}
                <b>your photos, elevation labels, WIN_REFs, and annotations are
                safe on the server</b>. Close this dialog, then click AI Measure
                → Resume to restore state and try again.
              </div>
            </div>
          </div>
          <details className="mb-4 text-[10px] text-[var(--muted)] font-mono bg-[var(--surface-muted)] p-2 border border-[var(--border)]">
            <summary className="cursor-pointer uppercase tracking-wider font-bold">
              Technical detail
            </summary>
            <div className="mt-2 whitespace-pre-wrap break-words">{msg}</div>
          </details>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={this.handleReset}
              className="px-3 py-1.5 bg-[var(--surface-muted)] hover:bg-[var(--surface)] border border-[var(--border)] text-xs font-bold uppercase tracking-wider"
              data-testid="annotator-error-retry"
            >
              Retry annotator
            </button>
            <button
              type="button"
              onClick={this.handleClose}
              className="px-3 py-1.5 bg-[var(--danger)] hover:opacity-90 text-white text-xs font-bold uppercase tracking-wider"
              data-testid="annotator-error-close"
            >
              Close annotator
            </button>
          </div>
        </div>
      </div>
    );
  }
}
