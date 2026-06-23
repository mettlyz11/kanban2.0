import LLMUsage from "./pages/LLMUsage";
import * as Sentry from "@sentry/react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { useLocation } from "react-router-dom";
import { useEffect } from "react";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Projects from "./pages/Projects";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Tasks from "./pages/Tasks";
import Settings from "./pages/Settings";
import ManualReview from "./pages/ManualReview";
import DailyReviews from "./pages/DailyReviews";
import Skills from "./pages/Skills";
import Stocks from "./pages/Stocks";
import LLMConfigs from "./pages/LLMConfigs";
import Architecture from "./pages/Architecture";
import Brain from "./pages/Brain";
import CalcTasks from "./pages/CalcTasks";
import CalendarPage from "./pages/CalendarPage";
import Chat from "./pages/Chat";
import RecurringTasks from "./pages/RecurringTasks";
import AuditRepair from './pages/AuditRepair';
import KTConfig from "./pages/KTConfig";
import SystemMap from "./pages/SystemMap";
import CommunicationHub from "./pages/CommunicationHub";
import CompanyInfo from "./pages/CompanyInfo";
import CompanyList from "./pages/CompanyList";
import Cron from "./pages/Cron";
import DuanBoshi from "./pages/DuanBoshi";
import Emails from "./pages/Emails";
import Goals from "./pages/Goals";
import Health from "./pages/Health";
import Helight from "./pages/Helight";
import LiuYuzhou from "./pages/LiuYuzhou";
import MeetingNotes from "./pages/MeetingNotes";
import Molecules from "./pages/Molecules";
import MyGoals from "./pages/MyGoals";
import Perception from "./pages/Perception";
import PerceptionMonitor from "./pages/PerceptionMonitor";
import PersonalInfo from "./pages/PersonalInfo";
import ProjectDesign from "./pages/ProjectDesign";
import Reactions from "./pages/Reactions";
import ResearchNotes from "./pages/ResearchNotes";
import Resources from "./pages/Resources";
import RipplePanorama from "./pages/RipplePanorama";
import EvolutionTrend from "./pages/EvolutionTrend";
import SystemPages from "./pages/SystemPages";
import XiaBoshi from "./pages/XiaBoshi";
import PeopleList from "./pages/PeopleList";
import SelfDrivingSystem from './pages/SelfDrivingSystem';
import Pepi from "./pages/Pepi";
import StrategicMap from "./pages/StrategicMap";
import Cockpit from "./pages/Cockpit";
import RemoteControl from './pages/RemoteControl'
import SDSConsole from './pages/SDSConsole'
import { RemoteDesktop } from './pages/RemoteDesktop'
import SystemSync from "./pages/SystemSync"
import ResourceLibrary from "./pages/ResourceLibrary"
import AuditLog from './pages/AuditLog'
import LLMGlobalContext from './pages/LLMGlobalContext'
import ResearchDaily from './pages/ResearchDaily'
import StrategicDocs from './pages/StrategicDocs'
import LLMProviders from './pages/LLMProviders'
import KnowledgeLibrary from './pages/KnowledgeLibrary'
import Contacts from './pages/Contacts'
import SysConfig from './pages/SysConfig'
import KanbanOverview from './pages/KanbanOverview'
import ActorPipeline from "./pages/ActorPipeline"
import SDSCrewDialogue from "./pages/SDSCrewDialogue"

function LocationTracker() {
  const location = useLocation();
  useEffect(() => {
    Sentry.addBreadcrumb({
      category: "navigation",
      message: "Navigate to " + location.pathname,
      level: "info",
      data: { pathname: location.pathname, search: location.search }
    });
    Sentry.captureMessage("页面切换: " + location.pathname, {
      level: "info",
      tags: { page: location.pathname, type: "page_view" }
    });
  }, [location]);
  return null;
}

export default function Router() {
  return (
    <BrowserRouter>
      <LocationTracker />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute><Layout>{undefined}</Layout></ProtectedRoute>}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/review" element={<ManualReview />} />
          <Route path="/daily-reviews" element={<DailyReviews />} />
          <Route path="/skills" element={<Skills />} />
          <Route path="/stocks" element={<Stocks />} />
          <Route path="/llm-configs" element={<LLMConfigs />} />
          <Route path="/llm-usage" element={<LLMUsage />} />
          <Route path="/llm-global-context" element={<LLMGlobalContext />} />
          <Route path="/architecture" element={<Architecture />} />
          <Route path="/brain" element={<Brain />} />
          <Route path="/calc-tasks" element={<CalcTasks />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/communication" element={<CommunicationHub />} />
          <Route path="/company" element={<CompanyList />} />
          <Route path="/company/helight" element={<Helight />} />
          <Route path="/company/:id" element={<CompanyInfo />} />
          <Route path="/cron" element={<Cron />} />
          <Route path="/emails" element={<Emails />} />
          <Route path="/goals" element={<Goals />} />
          <Route path="/my-goals" element={<MyGoals />} />
          <Route path="/health" element={<Health />} />
          <Route path="/molecules" element={<Molecules />} />
          <Route path="/perception" element={<Perception />} />
          <Route path="/perception-monitor" element={<PerceptionMonitor />} />
          <Route path="/personal" element={<PeopleList />} />
          <Route path="/personal/2" element={<XiaBoshi />} />
          <Route path="/personal/3" element={<DuanBoshi />} />
          <Route path="/personal/4" element={<LiuYuzhou />} />
          <Route path="/personal/:id" element={<PersonalInfo />} />
          <Route path="/project-design" element={<ProjectDesign />} />
          <Route path="/reactions" element={<Reactions />} />
          <Route path="/research" element={<ResearchNotes />} />
          <Route path="/resources" element={<Resources />} />
          <Route path="/system-monitor" element={<SystemPages />} />
          <Route path="/meetings" element={<MeetingNotes />} />
          <Route path="/pepi" element={<Pepi />} />
          
          <Route path="/remote-control" element={<RemoteControl />} />
          <Route path="/sds-console" element={<SDSConsole />} />
          <Route path="/remote-desktop" element={<RemoteDesktop />} />
          <Route path="/audit-log" element={<AuditLog />} />
<Route path="/self-driving" element={<SelfDrivingSystem />} />
          <Route path="/strategic-map" element={<StrategicMap />} />
          {/* self-driving route added 2026-04-23 */}
          <Route path="/recurring-tasks" element={<RecurringTasks />} />
          <Route path="/system-map" element={<SystemMap />} />
          <Route path="/kt-config" element={<KTConfig />} />
          <Route path="/audit-repair" element={<AuditRepair />} />
          <Route path="/system-sync" element={<SystemSync />} />
          <Route path="/audit" element={<AuditLog />} />
          <Route path="/resource-library" element={<ResourceLibrary />} />
          <Route path="/cockpit" element={<Cockpit />} />
          <Route path="/panorama" element={<RipplePanorama />} />
          <Route path="/evolution-trend" element={<EvolutionTrend />} />
          <Route path="/research-daily" element={<ResearchDaily />} />
          <Route path="/strategic-docs" element={<StrategicDocs />} />
          <Route path="/llm-providers" element={<LLMProviders />} />
          <Route path="/knowledge-library" element={<KnowledgeLibrary />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/sys-config" element={<SysConfig />} />
          <Route path="/actor-pipeline" element={<ActorPipeline />} />
          <Route path="/overview" element={<KanbanOverview />} />
          <Route path="/sds-crew-dialogue" element={<SDSCrewDialogue />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}// BUILD_1781420464
