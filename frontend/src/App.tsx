import { Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/layouts/MainLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<DashboardPage />} />
        {/* Future routes will be added here in later phases */}
      </Route>
      <Route path="/404" element={<NotFoundPage />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  )
}

export default App
