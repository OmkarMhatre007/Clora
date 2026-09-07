import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import LiveExecutionDrawer from './components/LiveExecutionDrawer';
import LocalIntelligenceCard from './components/LocalIntelligenceCard';
import ErrorBoundary from './components/ErrorBoundary';

import WorkbenchView from './views/WorkbenchView';
import KnowledgeGraphView from './views/KnowledgeGraphView';
import DataSourcesView from './views/DataSourcesView';
import IntelligenceAgentsView from './views/IntelligenceAgentsView';
import IntelligenceModelsView from './views/IntelligenceModelsView';
import SovereigntyView from './views/SovereigntyView';

import { getWorkspaces, getWorkspaceFiles, getWorkspaceQueries, getModels } from './services/api';

export default function App() {
  const [activeView, setActiveView] = useState('workbench');
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState('default-workspace');
  const [userRole, setUserRole] = useState('maintenance_engineer');
  const [activeQuery, setActiveQuery] = useState(null);
  const [latestQuery, setLatestQuery] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [liveStats, setLiveStats] = useState({ filesCount: 4, queriesCount: 0, activeModel: 'llama3.2:3b' });

  const refreshGlobalData = async (wsId = activeWorkspaceId) => {
    try {
      const [wsList, files, queries, modelsData] = await Promise.all([
        getWorkspaces(),
        getWorkspaceFiles(wsId),
        getWorkspaceQueries(wsId),
        getModels()
      ]);

      if (wsList && wsList.length > 0) setWorkspaces(wsList);
      if (queries && queries.length > 0) {
        setLatestQuery(queries[0]);
      }
      setLiveStats({
        filesCount: files?.length || 0,
        queriesCount: queries?.length || 0,
        activeModel: modelsData?.active_model || 'llama3.2:3b'
      });
    } catch (err) {
      console.warn('Error refreshing app state:', err);
    }
  };

  useEffect(() => {
    refreshGlobalData(activeWorkspaceId);
  }, [activeWorkspaceId]);

  const handleQueryUpdate = (query) => {
    setActiveQuery(query);
    if (query.status === 'processing') {
      setIsProcessing(true);
    } else {
      setIsProcessing(false);
      setLatestQuery(query);
      refreshGlobalData(activeWorkspaceId);
    }
  };

  const handleSelectEvidence = (source) => {
    // If user clicks a source from an investigation, navigate to Data Sources or Graph
    if (source.filename?.toLowerCase().includes('pid') || source.filename?.toLowerCase().includes('circuit')) {
      setActiveView('graph');
    } else {
      setActiveView('data-sources');
    }
  };

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-[#141312] text-[#f5f2ed] flex flex-col font-sans selection:bg-[#d9825b] selection:text-white">
        {/* Top Header with Target Air-Gapped Status Widget & RBAC Role Switcher */}
        <Header
          workspaces={workspaces}
          activeWorkspaceId={activeWorkspaceId}
          onWorkspaceChange={(id) => {
            setActiveWorkspaceId(id);
            setActiveQuery(null);
          }}
          userRole={userRole}
          onRoleChange={setUserRole}
        />

        {/* Main Layout Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Categorized Left Sidebar */}
          <Sidebar
            activeView={activeView}
            onViewChange={setActiveView}
            liveStats={liveStats}
          />

          {/* Center Main Content Area */}
          <main className="flex-1 p-6 overflow-y-auto max-w-[1680px] mx-auto w-full transition-all">
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
              {/* Main View Area */}
              <div className={`${activeView === 'workbench' || activeView === 'home' ? 'xl:col-span-8' : 'xl:col-span-12'}`}>
                {(activeView === 'workbench' || activeView === 'home') && (
                  <WorkbenchView
                    workspaceId={activeWorkspaceId}
                    userRole={userRole}
                    onSelectEvidence={handleSelectEvidence}
                    onQueryUpdate={handleQueryUpdate}
                  />
                )}
                {(activeView === 'graph' || activeView === 'knowledge') && (
                  <KnowledgeGraphView />
                )}
                {activeView === 'data-sources' && (
                  <DataSourcesView workspaceId={activeWorkspaceId} />
                )}
                {activeView === 'intelligence-agents' && (
                  <IntelligenceAgentsView />
                )}
                {activeView === 'intelligence-models' && (
                  <IntelligenceModelsView />
                )}
                {(activeView === 'sovereignty' || activeView === 'audit-trail' || activeView === 'settings') && (
                  <SovereigntyView />
                )}
              </div>

              {/* Right Execution Sidebar (When in Workbench view) */}
              {(activeView === 'workbench' || activeView === 'home') && (
                <div className="xl:col-span-4 space-y-5">
                  <LiveExecutionDrawer
                    activeQuery={activeQuery}
                    latestQuery={latestQuery}
                    isProcessing={isProcessing}
                    onViewTrace={() => setActiveView('sovereignty')}
                  />
                  <LocalIntelligenceCard
                    filesCount={liveStats.filesCount}
                    activeModel={liveStats.activeModel}
                    onNavigate={setActiveView}
                  />
                </div>
              )}
            </div>
          </main>
        </div>
      </div>
    </ErrorBoundary>
  );
}
