import React from 'react';
import { AlertTriangle, RefreshCw, ShieldCheck } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('CLORA UI Runtime Error caught by ErrorBoundary:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#141312] text-[#f5f2ed] flex items-center justify-center p-6">
          <div className="clora-card max-w-lg w-full p-6 space-y-4 border border-[#d9825b]/50 shadow-2xl text-center">
            <div className="w-12 h-12 rounded-full bg-[#291f19] border border-[#d9825b] flex items-center justify-center mx-auto text-[#d9825b]">
              <AlertTriangle size={24} />
            </div>
            
            <div className="space-y-1">
              <h2 className="text-lg font-bold font-display text-[#f5f2ed]">UI View Render State Recovered</h2>
              <p className="text-xs text-[#a09a90]">
                A component encountered a rendering exception. Local air-gap backend state and security firewalls remain fully intact.
              </p>
            </div>

            {this.state.error?.message && (
              <div className="p-3 rounded-lg bg-[#1a1715] border border-[#2e2a25] text-left text-[11px] font-mono text-[#f87171] overflow-x-auto max-h-32">
                {this.state.error.message}
              </div>
            )}

            <div className="pt-2 flex justify-center gap-3">
              <button
                onClick={this.handleReset}
                className="btn-copper text-xs py-2 px-5 flex items-center gap-2"
              >
                <RefreshCw size={14} />
                <span>Reload Workbench</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
