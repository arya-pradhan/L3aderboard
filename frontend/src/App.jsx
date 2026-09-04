import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import SteamCallback from "./pages/SteamCallback.jsx";
import Discover from "./pages/Discover.jsx";
import Profile from "./pages/Profile.jsx";
import Feed from "./pages/Feed.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/auth/steam" element={<SteamCallback />} />

      <Route element={<AppLayout />}>
        <Route path="/" element={<Discover />} />
        <Route path="/library" element={<Profile />} />
        <Route path="/u/:username" element={<Profile />} />
        <Route path="/feed" element={<Feed />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
