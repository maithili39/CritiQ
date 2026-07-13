import { Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import MySessions from "@/pages/MySessions";
import InterviewSetup from "@/pages/InterviewSetup";
import Interview from "@/pages/Interview";
import Report from "@/pages/Report";
import CandidateInterview from "@/pages/CandidateInterview";
import ProtectedRoute from "@/components/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/sessions" element={<ProtectedRoute><MySessions /></ProtectedRoute>} />
      <Route path="/interview/setup" element={<ProtectedRoute><InterviewSetup /></ProtectedRoute>} />
      <Route path="/interview/:id" element={<ProtectedRoute><Interview /></ProtectedRoute>} />
      <Route path="/interview/:id/report" element={<ProtectedRoute><Report /></ProtectedRoute>} />
      {/* Public: candidate invite link, authenticated by the session's access token, not login */}
      <Route path="/take/:sessionId" element={<CandidateInterview />} />
    </Routes>
  );
}
