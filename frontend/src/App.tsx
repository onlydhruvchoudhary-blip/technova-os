import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './store'
import { Spinner } from './ui'
import Layout from './Layout'
import Auth from './pages/Auth'
import Dashboard from './pages/Dashboard'
import Academy from './pages/Academy'
import CourseView from './pages/CourseView'
import LessonView from './pages/LessonView'
import Skills from './pages/Skills'
import Challenges from './pages/Challenges'
import ChallengeView from './pages/ChallengeView'
import Projects from './pages/Projects'
import ProjectView from './pages/ProjectView'
import Events from './pages/Events'
import Competitions from './pages/Competitions'
import CompetitionView from './pages/CompetitionView'
import Leaderboard from './pages/Leaderboard'
import Profile from './pages/Profile'
import Members from './pages/Members'
import Governance from './pages/Governance'
import Store from './pages/Store'
import Grading from './pages/Grading'
import GradingView from './pages/GradingView'
import Resources from './pages/Resources'
import Showcase from './pages/Showcase'
import Activity from './pages/Activity'
import Admin from './pages/Admin'
import CommandCenter from './pages/CommandCenter'
import Verify from './pages/Verify'

export default function App() {
  const { user, loading } = useAuth()
  const loc = useLocation()

  if (loading) return <Spinner />

  // Public routes (no auth required)
  if (loc.pathname.startsWith('/verify/')) {
    return <Routes><Route path="/verify/:uid" element={<Verify />} /></Routes>
  }
  if (loc.pathname === '/command-center') {
    return <Routes><Route path="/command-center" element={<CommandCenter />} /></Routes>
  }

  if (!user) return <Auth />

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/academy" element={<Academy />} />
        <Route path="/academy/:slug" element={<CourseView />} />
        <Route path="/lesson/:id" element={<LessonView />} />
        <Route path="/skills" element={<Skills />} />
        <Route path="/challenges" element={<Challenges />} />
        <Route path="/challenges/:slug" element={<ChallengeView />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:slug" element={<ProjectView />} />
        <Route path="/events" element={<Events />} />
        <Route path="/competitions" element={<Competitions />} />
        <Route path="/competitions/:id" element={<CompetitionView />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/members" element={<Members />} />
        <Route path="/governance" element={<Governance />} />
        <Route path="/store" element={<Store />} />
        <Route path="/grading" element={<Grading />} />
        <Route path="/grading/:id" element={<GradingView />} />
        <Route path="/members/:id" element={<Profile />} />
        <Route path="/resources" element={<Resources />} />
        <Route path="/showcase" element={<Showcase />} />
        <Route path="/activity" element={<Activity />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  )
}
