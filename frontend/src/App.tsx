import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Projects } from './pages/Projects'
import { Tasks } from './pages/Tasks'
import { Cron } from './pages/Cron'
import { Stocks } from './pages/Stocks'
import { ManualReview } from './pages/ManualReview'
import { Skills } from './pages/Skills'
import { CalcTasks } from './pages/CalcTasks'
import { Molecules } from './pages/Molecules'
import { Reactions } from './pages/Reactions'
import { Chat } from './pages/Chat'
import { Emails } from './pages/Emails'
import { Brain } from './pages/Brain'
import { Pepi } from './pages/Pepi'
import { SystemMonitor, AccessStats } from './pages/SystemPages'
import { VersionLogs } from './pages/VersionLogs'
import { Architecture } from './pages/Architecture'
import { LLMConfigs } from './pages/LLMConfigs'
import { ResearchNotes } from './pages/ResearchNotes'
import { MeetingNotes } from './pages/MeetingNotes'
import { DailyReviews } from './pages/DailyReviews'
import { Resources } from './pages/Resources'
import './components/Layout.css'

// 路由守卫组件
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function AppRoutes() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" /> : <Login />} />
      <Route path="/" element={<PrivateRoute><Layout><Dashboard /></Layout></PrivateRoute>} />
      <Route path="/projects" element={<PrivateRoute><Layout><Projects /></Layout></PrivateRoute>} />
      <Route path="/tasks" element={<PrivateRoute><Layout><Tasks /></Layout></PrivateRoute>} />
      <Route path="/brain" element={<PrivateRoute><Layout><Brain /></Layout></PrivateRoute>} />
      <Route path="/cron" element={<PrivateRoute><Layout><Cron /></Layout></PrivateRoute>} />
      <Route path="/stocks" element={<PrivateRoute><Layout><Stocks /></Layout></PrivateRoute>} />
      <Route path="/review" element={<PrivateRoute><Layout><ManualReview /></Layout></PrivateRoute>} />
      <Route path="/skills" element={<PrivateRoute><Layout><Skills /></Layout></PrivateRoute>} />
      <Route path="/calc-tasks" element={<PrivateRoute><Layout><CalcTasks /></Layout></PrivateRoute>} />
      <Route path="/molecules" element={<PrivateRoute><Layout><Molecules /></Layout></PrivateRoute>} />
      <Route path="/reactions" element={<PrivateRoute><Layout><Reactions /></Layout></PrivateRoute>} />
      <Route path="/chat" element={<PrivateRoute><Layout><Chat /></Layout></PrivateRoute>} />
      <Route path="/emails" element={<PrivateRoute><Layout><Emails /></Layout></PrivateRoute>} />
      <Route path="/pepi" element={<PrivateRoute><Layout><Pepi /></Layout></PrivateRoute>} />
      <Route path="/system-monitor" element={<PrivateRoute><Layout><SystemMonitor /></Layout></PrivateRoute>} />
      <Route path="/access-stats" element={<PrivateRoute><Layout><AccessStats /></Layout></PrivateRoute>} />
      <Route path="/version-logs" element={<PrivateRoute><Layout><VersionLogs /></Layout></PrivateRoute>} />
      <Route path="/llm-configs" element={<PrivateRoute><Layout><LLMConfigs /></Layout></PrivateRoute>} />
      <Route path="/research" element={<PrivateRoute><Layout><ResearchNotes /></Layout></PrivateRoute>} />
      <Route path="/meetings" element={<PrivateRoute><Layout><MeetingNotes /></Layout></PrivateRoute>} />
      <Route path="/daily-reviews" element={<PrivateRoute><Layout><DailyReviews /></Layout></PrivateRoute>} />
      <Route path="/architecture" element={<PrivateRoute><Layout><Architecture /></Layout></PrivateRoute>} />
      <Route path="/resources" element={<PrivateRoute><Layout><Resources /></Layout></PrivateRoute>} />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
