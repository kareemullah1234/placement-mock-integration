import { useEffect, useState } from "react"
import AdminNavbar from "../components/AdminNavbar"
import API from "../api/api"

function AdminDashboard(){

const [stats,setStats] = useState({
candidates:0,
companies:0,
jobs:0
})

useEffect(()=>{
fetchStats()
},[])

const fetchStats = async () => {

try{
const res = await API.get("common/admin/stats/")

console.log(res.data)

setStats(res.data)

}
catch(error){
    console.log(error);
}
}

return(

<div>

<AdminNavbar/>

<div className="main-container">

<h2>Admin Dashboard</h2>

<div className="dashboard-cards">

<div className="card">
<h3>Total Candidates</h3>
<p>{stats.candidates}</p>
</div>

<div className="card">
<h3>Total Companies</h3>
<p>{stats.companies}</p>
</div>

<div className="card">
<h3>Total Jobs</h3>
<p>{stats.jobs}</p>
</div>

</div>

</div>

</div>

)

}

export default AdminDashboard