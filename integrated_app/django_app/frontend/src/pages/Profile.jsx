import {useState,useEffect} from "react"
import Navbar from "../components/Navbar"
import API from "../api/api"
import {useNavigate} from "react-router-dom"

function Profile(){

const navigate = useNavigate()

const [name,setName]=useState("")
const [email,setEmail]=useState("")
const [phone,setPhone]=useState("")
const [resume,setResume]=useState(null)

useEffect(()=>{

fetchProfile()

},[])

const fetchProfile = async ()=>{

const user_id = localStorage.getItem("user_id")

const res = await API.get(`/candidates/profile/get/?user_id=${user_id}`)

setName(res.data.name)
setEmail(res.data.email)
setPhone(res.data.phone)

}

const saveProfile = async()=>{

const formData=new FormData()

formData.append("user_id",localStorage.getItem("user_id"))
formData.append("phone",phone)

if(resume){
formData.append("resume",resume)
}

await API.post("/candidates/profile/update/",formData)

alert("Profile Updated")

navigate("/dashboard")

}

return(

<div>

<Navbar/>

<div className="page-container">

<div className="card">

<h2>Profile</h2>

<h5>Name</h5>
<input
className="input-field"
value={name}
disabled
/>

<h5>Email</h5>
<input
className="input-field"
value={email}
disabled
/>

<h5>Phone Number</h5>
<input
className="input-field"
value={phone}
onChange={(e)=>setPhone(e.target.value)}
/>

<h5>Upload Resume</h5>
<input
className="file-input"
type="file"
onChange={(e)=>setResume(e.target.files[0])}
/>

<button
className="btn"
onClick={saveProfile}
>
Save Profile
</button>

</div>

</div>

</div>

)

}

export default Profile