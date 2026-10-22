import { HashRouter, Route, Routes } from 'react-router-dom'
import Layout from './layout/Layout'
import AnalyticsPage from './pages/AnalyticsPage'
import ExperimentPage from './pages/ExperimentPage'
import NodeMonitorPage from './pages/NodeMonitorPage'
import OverviewPage from './pages/OverviewPage'
import SchedulerPage from './pages/SchedulerPage'
import { AppStateProvider } from './state'

export default function App() {
  return (
    <AppStateProvider>
      <HashRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<OverviewPage />} />
            <Route path="nodes" element={<NodeMonitorPage />} />
            <Route path="scheduler" element={<SchedulerPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="experiment" element={<ExperimentPage />} />
          </Route>
        </Routes>
      </HashRouter>
    </AppStateProvider>
  )
}
