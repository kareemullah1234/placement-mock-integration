import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import Jobs from "./pages/Jobs";
import Applications from "./pages/Applications";
import AdminDashboard from "./pages/AdminDashboard";  
import AdminUsers from "./pages/AdminUsers";


function App() {
  return (
    <Router>

      <Navbar />

      <div className="main-container">
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/admin/dashboard" element={<AdminDashboard/>}/>
          <Route path="/admin/users" element={<AdminUsers/>}/>
          <Route path="/profile" element={<Profile/>}/>
          <Route path="/applications" element={<Applications/>}/>
        </Routes>
      </div>

    </Router>
  );
}

export default App;