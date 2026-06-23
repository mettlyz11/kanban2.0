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
import ActorPipeline from './pages/ActorPipeline'
import { LLMConfigs } from './pages/LLMConfigs'
import LLMGlobalContext from './pages/LLMGlobalContext'
import { ResearchNotes } from './pages/ResearchNotes'
import { MeetingNotes } from './pages/MeetingNotes'
import { DailyReviews } from './pages/DailyReviews'
import AuditLog from './pages/AuditLog'
import AuditRepair from './pages/AuditRepair'
import Contacts from './pages/Contacts'
import DependencyGraph from './pages/DependencyGraph'
import EvolutionTrend from './pages/EvolutionTrend'
import GardenDashboard from './pages/GardenDashboard'
import KTConfig from './pages/KTConfig'
import KanbanOverview from './pages/KanbanOverview'
import KnowledgeLibrary from './pages/KnowledgeLibrary'
import LLMProviders from './pages/LLMProviders'
import LLMUsage from './pages/LLMUsage'
import Marketplace from './pages/Marketplace'
import PaymentPage from './pages/PaymentPage'
import Pricing from './pages/Pricing'
import RecurringTasks from './pages/RecurringTasks'
import RemoteControl from './pages/RemoteControl'
import { RemoteDesktop } from './pages/RemoteDesktop'
import RipplePanorama from './pages/RipplePanorama'
import SDSConsole from './pages/SDSConsole'
import { Resources } from './pages/Resources'
import ResearchDaily from './pages/ResearchDaily'
import ResourceLibrary from './pages/ResourceLibrary'
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
import SDSCrewDialogue from './pages/SDSCrewDialogue'
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
      <Route path="/actor-pipeline" element={<PrivateRoute><Layout><ActorPipeline /></Layout></PrivateRoute>} />
      <Route path="/reactions" element={<PrivateRoute><Layout><Reactions /></Layout></PrivateRoute>} />
      <Route path="/chat" element={<PrivateRoute><Layout><Chat /></Layout></PrivateRoute>} />
      <Route path="/emails" element={<PrivateRoute><Layout><Emails /></Layout></PrivateRoute>} />
      <Route path="/pepi" element={<PrivateRoute><Layout><Pepi /></Layout></PrivateRoute>} />
      <Route path="/system-monitor" element={<PrivateRoute><Layout><SystemMonitor /></Layout></PrivateRoute>} />
      <Route path="/access-stats" element={<PrivateRoute><Layout><AccessStats /></Layout></PrivateRoute>} />
      <Route path="/version-logs" element={<PrivateRoute><Layout><VersionLogs /></Layout></PrivateRoute>} />
      <Route path="/llm-configs" element={<PrivateRoute><Layout><LLMConfigs /></Layout></PrivateRoute>} />
      <Route path="/llm-global-context" element={<PrivateRoute><Layout><LLMGlobalContext /></Layout></PrivateRoute>} />
      <Route path="/research" element={<PrivateRoute><Layout><ResearchNotes /></Layout></PrivateRoute>} />
      <Route path="/meetings" element={<PrivateRoute><Layout><MeetingNotes /></Layout></PrivateRoute>} />
      <Route path="/daily-reviews" element={<PrivateRoute><Layout><DailyReviews /></Layout></PrivateRoute>} />
      <Route path="/architecture" element={<PrivateRoute><Layout><Architecture /></Layout></PrivateRoute>} />
      <Route path="/resources" element={<PrivateRoute><Layout><Resources /></Layout></PrivateRoute>} />
      <Route path="/research-daily" element={<PrivateRoute><Layout><ResearchDaily /></Layout></PrivateRoute>} />
      <Route path="/resource-library" element={<PrivateRoute><Layout><ResourceLibrary /></Layout></PrivateRoute>} />
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


          <Route path="/audit-log" element={<PrivateRoute><Layout><AuditLog /></Layout></PrivateRoute>} />
      <Route path="/audit-repair" element={<PrivateRoute><Layout><AuditRepair /></Layout></PrivateRoute>} />
      <Route path="/contacts" element={<PrivateRoute><Layout><Contacts /></Layout></PrivateRoute>} />
      <Route path="/dependency-graph" element={<PrivateRoute><Layout><DependencyGraph /></Layout></PrivateRoute>} />
      <Route path="/evolution-trend" element={<PrivateRoute><Layout><EvolutionTrend /></Layout></PrivateRoute>} />
      <Route path="/garden-dashboard" element={<PrivateRoute><Layout><GardenDashboard /></Layout></PrivateRoute>} />
      <Route path="/kt-config" element={<PrivateRoute><Layout><KTConfig /></Layout></PrivateRoute>} />
      <Route path="/overview" element={<PrivateRoute><Layout><KanbanOverview /></Layout></PrivateRoute>} />
      <Route path="/knowledge-library" element={<PrivateRoute><Layout><KnowledgeLibrary /></Layout></PrivateRoute>} />
      <Route path="/llm-providers" element={<PrivateRoute><Layout><LLMProviders /></Layout></PrivateRoute>} />
      <Route path="/llm-usage" element={<PrivateRoute><Layout><LLMUsage /></Layout></PrivateRoute>} />
      <Route path="/marketplace" element={<PrivateRoute><Layout><Marketplace /></Layout></PrivateRoute>} />
      <Route path="/payment" element={<PrivateRoute><Layout><PaymentPage /></Layout></PrivateRoute>} />
      <Route path="/pricing" element={<PrivateRoute><Layout><Pricing /></Layout></PrivateRoute>} />
      <Route path="/recurring-tasks" element={<PrivateRoute><Layout><RecurringTasks /></Layout></PrivateRoute>} />
      <Route path="/remote-control" element={<PrivateRoute><Layout><RemoteControl /></Layout></PrivateRoute>} />
      <Route path="/remote-desktop" element={<PrivateRoute><Layout><RemoteDesktop /></Layout></PrivateRoute>} />
      <Route path="/panorama" element={<PrivateRoute><Layout><RipplePanorama /></Layout></PrivateRoute>} />
      <Route path="/sds-console" element={<PrivateRoute><Layout><SDSConsole /></Layout></PrivateRoute>} />
      <Route path="/sds-crew-dialogue" element={<PrivateRoute><Layout><SDSCrewDialogue /></Layout></PrivateRoute>} />
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
