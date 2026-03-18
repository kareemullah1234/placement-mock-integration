import { Link } from "react-router-dom"

function AdminNavbar(){

return(

<div className="navbar">

<h2>AI Placement Portal</h2>

<div className="nav-links">

<Link to="/admin/dashboard">Dashboard</Link>

<Link to="/admin/users">Users</Link>

<Link to="/admin/companies">Companies</Link>

<Link to="/admin/jobs">Jobs</Link>

<Link to="/login">Logout</Link>

</div>

</div>

)

}

export default AdminNavbar