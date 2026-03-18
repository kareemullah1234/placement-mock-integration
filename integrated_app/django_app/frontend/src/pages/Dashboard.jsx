import Navbar from "../components/Navbar"
import { useNavigate } from "react-router-dom"

function Dashboard(){

const navigate = useNavigate()

const username = localStorage.getItem("username")

return(

<div>

<Navbar/>

<div className="dashboard-container">

<h2 className="welcome-title">
Welcome {username} 👋
</h2>

<p className="quote">
"Opportunities don't happen. You create them."
</p>

<div className="dashboard-layout">

{/* LEFT SIDE */}

<div className="dashboard-left">

<div
className="dashboard-card"
onClick={()=>navigate("/jobs")}
>
<h3>💼 Browse Jobs</h3>
<p>Explore jobs you are eligible for</p>
</div>

<div
className="dashboard-card"
onClick={()=>navigate("/applications")}
>
<h3>📄 My Applications</h3>
<p>Track the jobs you applied for</p>
</div>

<div
className="dashboard-card"
onClick={()=>navigate("/profile")}
>
<h3>👤 Complete Profile</h3>
<p>Update phone number and resume</p>
</div>

</div>

{/* RIGHT SIDE */}

<div className="dashboard-right">

<div className="info-card">
<h3>📢 Latest Updates</h3>
<p>New companies are posting jobs every week.</p>
</div>

<div className="info-card">
<h3>🎯 Career Tip</h3>
<p>Keep your resume updated to increase your chances of getting shortlisted.</p>
</div>

<div className="info-card">
<h3>📧 Contact Support</h3>
<p>Email: placementportal@gmail.com</p>
<p>Phone: +91 9876543210</p>
</div>

</div>

</div>

</div>

</div>

)

}

export default Dashboard