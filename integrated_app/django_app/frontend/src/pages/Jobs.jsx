import {useEffect,useState} from "react"
import Navbar from "../components/Navbar"
import API from "../api/api"

function Jobs(){

const [jobs,setJobs] = useState([])

useEffect(()=>{

API.get("/api/jobs/")
.then(res=>setJobs(res.data))

},[])

return(

<div>

<Navbar/>

<div style={{padding:"40px"}}>

<h2>Available Jobs</h2>

{jobs.map(job=>(

<div key={job.id} style={card}>

<h3>{job.title}</h3>

<p>{job.company}</p>

<button>Apply</button>

</div>

))}

</div>

</div>

)

}

const card={
border:"1px solid #ddd",
padding:"20px",
margin:"10px",
borderRadius:"8px"
}

export default Jobs