import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to console or error reporting service
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo
    });
    
    // Log to console for development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error details:', error);
      console.error('Stack trace:', errorInfo.componentStack);
    }
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
          <div className="max-w-2xl w-full bg-slate-900 rounded-lg border border-red-500/20 p-6 space-y-6">
            {/* Error Icon */}
            <div className="flex items-center gap-3 text-red-500">
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                width="48" 
                height="48" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2" 
                strokeLinecap="round" 
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
              </svg>
              <h1 className="text-3xl font-bold">Something went wrong</h1>
            </div>

            {/* Error Message */}
            <div className="space-y-4">
              {this.state.error && (
                <div>
                  <h2 className="text-lg font-semibold text-slate-300">Error:</h2>
                  <p className="text-red-400 font-mono break-all bg-slate-950 p-3 rounded border border-red-500/20">
                    {this.state.error.toString()}
                  </p>
                </div>
              )}

              {/* Error Details */}
              {this.state.errorInfo && (
                <div>
                  <h2 className="text-lg font-semibold text-slate-300">Error Location:</h2>
                  <div className="text-slate-400 text-sm font-mono bg-slate-950 p-3 rounded border border-red-500/20 max-h-60 overflow-auto">
                    {this.state.errorInfo.componentStack}
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-4">
              <Button 
                onClick={this.handleReset}
                className="flex-1 justify-center"
              >
                Try Again
              </Button>
              
              <Button 
                onClick={() => window.location.href = '/'}
                variant="outline"
                className="flex-1 justify-center"
              >
                Go to Home
              </Button>
            </div>

            {/* Debug Info (Development only) */}
            {process.env.NODE_ENV === 'development' && (
              <div className="border-t border-slate-800 pt-4">
                <details className="space-y-2">
                  <summary className="text-sm text-slate-500 cursor-pointer hover:text-red-400 transition-colors">
                    Show Debug Information
                  </summary>
                  <div className="text-xs text-slate-600 font-mono space-y-1 mt-2">
                    <p>Error: {this.state.error?.toString()}</p>
                    <p>Component Stack:</p>
                    <pre className="text-slate-500">
                      {this.state.errorInfo?.componentStack}
                    </pre>
                  </div>
                </details>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
