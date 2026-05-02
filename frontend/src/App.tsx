import * as Sentry from "@sentry/react"
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Projects } from './pages/Projects'
import Tasks from './pages/Tasks'
import { Cron } from './pages/Cron'
import { Stocks } from './pages/Stocks'
import { ManualReview } from './pages/ManualReview'
import { Skills } from './pages/Skills'
import { CalcTasks } from './pages/CalcTasks'
import MyGoals from './pages/MyGoals'
import { Goals } from './pages/Goals'
import { ResourceMonitor } from './pages/ResourceMonitor'
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
import Calendar from './pages/CalendarPage'
import { CalendarSettings } from './pages/CalendarSettings'
import { PerceptionAgent } from './pages/Perception'
import { PerceptionMonitor } from './pages/PerceptionMonitor'
import { CommunicationHub } from './pages/CommunicationHub'
import { Health } from './pages/Health'
import { PersonalInfo } from './pages/PersonalInfo'
import { LiuYuzhou } from './pages/LiuYuzhou'
import { CompanyalInfo as CompanyInfo } from './pages/CompanyInfo'
import { Helight } from './pages/Helight'
import { ProjectDesign } from './pages/ProjectDesign'
import { ProjectDocuments } from './pages/ProjectDocuments'
import SelfDrivingSystem from './pages/SelfDrivingSystem'
import Cockpit from './pages/Cockpit'
import './App.css'
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
      <Route path="/projects/:projectId/documents" element={<PrivateRoute><Layout><ProjectDocuments /></Layout></PrivateRoute>} />
      <Route path="/tasks" element={<PrivateRoute><Layout><Tasks /></Layout></PrivateRoute>} />
      <Route path="/goals" element={<PrivateRoute><Layout><Goals /></Layout></PrivateRoute>} />
      <Route path="/my-goals" element={<PrivateRoute><Layout><MyGoals /></Layout></PrivateRoute>} />
      <Route path="/resource-monitor" element={<PrivateRoute><Layout><ResourceMonitor /></Layout></PrivateRoute>} />
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
      <Route path="/calendar" element={<PrivateRoute><Layout><Calendar /></Layout></PrivateRoute>} />
      <Route path="/calendar-settings" element={<PrivateRoute><Layout><CalendarSettings /></Layout></PrivateRoute>} />
      <Route path="/perception" element={<PrivateRoute><Layout><PerceptionAgent /></Layout></PrivateRoute>} />
      <Route path="/perception-monitor" element={<PrivateRoute><Layout><PerceptionMonitor /></Layout></PrivateRoute>} />
      <Route path="/communication" element={<PrivateRoute><Layout><CommunicationHub /></Layout></PrivateRoute>} />
      <Route path="/health" element={<PrivateRoute><Layout><Health /></Layout></PrivateRoute>} />
      <Route path="/personal" element={<PrivateRoute><Layout><PersonalInfo /></Layout></PrivateRoute>} />
      <Route path="/personal/:id" element={<PrivateRoute><Layout><PersonalInfo /></Layout></PrivateRoute>} />
      <Route path="/personal/liuyuzhou" element={<PrivateRoute><Layout><LiuYuzhou /></Layout></PrivateRoute>} />

      <Route path="/self-driving" element={<Layout><SelfDrivingSystem /></Layout>} />
      <Route path="/cockpit" element={<Layout><Cockpit /></Layout>} />
      <Route path="/company/:companyId" element={<PrivateRoute><Layout><Helight /></Layout></PrivateRoute>} />
      <Route path="/company" element={<PrivateRoute><Layout><CompanyInfo /></Layout></PrivateRoute>} />


    </Routes>
  )
}

function App() {
  Sentry.addBreadcrumb({
    category: "lifecycle",
    message: "App component mounted",
    level: "info"
  })
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

// BUILD_VERIFICATION_TOKEN_20260423_ABCDEF123
export default App
