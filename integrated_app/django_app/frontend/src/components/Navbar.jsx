import { Link, useNavigate } from "react-router-dom";

function Navbar(){

  const navigate = useNavigate();

  const handleLogout = () => {
    navigate("/");   // go to login page
  }

  return (

    <div className="navbar">

      <div className="logo">
        AI Placement Portal
      </div>

      <div className="nav-links">

        <Link to="/dashboard">Dashboard</Link>

        <Link to="/jobs">Jobs</Link>

        <Link to="/profile">Profile</Link>

        <button className="logout-btn" onClick={handleLogout}>
          Logout
        </button>

      </div>

    </div>

  )
}

export default Navbar;