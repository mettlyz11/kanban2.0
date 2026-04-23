import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./hooks/useAuth";
import Layout from "./components/Layout";
import Projects from "./pages/Projects";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Tasks from "./pages/Tasks";
import Users from "./pages/PersonalInfo";
import Health from "./pages/Health";
import Goals from "./pages/Goals";
import Brain from "./pages/Brain";
import Cron from "./pages/Cron";
import Stocks from "./pages/Stocks";
import PersonalInfo from "./pages/PersonalInfo";
import CompanyInfo from "./pages/CompanyInfo";
import ProjectDesign from "./pages/ProjectDesign";
import Resources from "./pages/Resources";
import ResearchNotes from "./pages/ResearchNotes";
import MeetingNotes from "./pages/MeetingNotes";
import Architecture from "./pages/Architecture";
import LLMConfigs from "./pages/LLMConfigs";
import Skills from "./pages/Skills";
import Molecules from "./pages/Molecules";
import Reactions from "./pages/Reactions";
import Emails from "./pages/Emails";
import CalcTasks from "./pages/CalcTasks";
import CommunicationHub from "./pages/CommunicationHub";
import Perception from "./pages/Perception";
import PerceptionMonitor from "./pages/PerceptionMonitor";
import DailyReviews from "./pages/DailyReviews";
import ManualReview from "./pages/ManualReview";
import Pepi from "./pages/Pepi";
import Chat from "./pages/Chat";
import Helight from "./pages/Helight";
import MyGoals from "./pages/MyGoals";
import { Calendar } from "./pages/Calendar";
import { SystemMonitor } from "./pages/SystemPages";

export default function Router() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/users" element={<Users />} />
            <Route path="/health" element={<Health />} />
            <Route path="/goals" element={<Goals />} />
            <Route path="/brain" element={<Brain />} />
            <Route path="/cron" element={<Cron />} />
            <Route path="/stocks" element={<Stocks />} />
            <Route path="/personal" element={<PersonalInfo />} />
            <Route path="/company" element={<CompanyInfo />} />
            <Route path="/project-design" element={<ProjectDesign />} />
            <Route path="/resources" element={<Resources />} />
            <Route path="/research" element={<ResearchNotes />} />
            <Route path="/meetings" element={<MeetingNotes />} />
            <Route path="/architecture" element={<Architecture />} />
            <Route path="/llm-configs" element={<LLMConfigs />} />
            <Route path="/skills" element={<Skills />} />
            <Route path="/molecules" element={<Molecules />} />
            <Route path="/reactions" element={<Reactions />} />
            <Route path="/emails" element={<Emails />} />
            <Route path="/calc-tasks" element={<CalcTasks />} />
            <Route path="/communication" element={<CommunicationHub />} />
            <Route path="/perception" element={<Perception />} />
            <Route path="/perception-monitor" element={<PerceptionMonitor />} />
            <Route path="/daily-reviews" element={<DailyReviews />} />
            <Route path="/review" element={<ManualReview />} />
            <Route path="/pepi" element={<Pepi />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/helight" element={<Helight />} />
            <Route path="/my-goals" element={<MyGoals />} />
            <Route path="/system-monitor" element={<SystemMonitor />} />
            <Route path="/calendar" element={<Calendar />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
