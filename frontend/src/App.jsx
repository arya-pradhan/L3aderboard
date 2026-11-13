import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout.jsx";
import Auth from "./pages/Auth.jsx";
import SteamCallback from "./pages/SteamCallback.jsx";
import Discover from "./pages/Discover.jsx";
import Profile from "./pages/Profile.jsx";
import Feed from "./pages/Feed.jsx";
import Chat from "./pages/Chat.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Auth key="login" mode="login" />} />
      <Route path="/register" element={<Auth key="register" mode="register" />} />
      <Route path="/auth/steam" element={<SteamCallback />} />

      <Route element={<AppLayout />}>
        <Route path="/" element={<Discover />} />
        <Route path="/library" element={<Profile />} />
        <Route path="/u/:username" element={<Profile />} />
        <Route path="/feed" element={<Feed />} />
        <Route path="/chat" element={<Chat />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
