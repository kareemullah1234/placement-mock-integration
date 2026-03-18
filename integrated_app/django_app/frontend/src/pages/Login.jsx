import { useState } from "react"
import { useNavigate } from "react-router-dom"
import API from "../api/api"
import Navbar from "../components/Navbar"

function Login(){

const navigate = useNavigate()

const [email,setEmail] = useState("")
const [password,setPassword] = useState("")

const login = async () => {

try{

const res = await API.post("/api/login/",{
username:email,
password:password
})

localStorage.setItem("user_id", res.data.user_id)

navigate("/dashboard")

}
catch(error){

console.log(error)

alert("Invalid Login")

}

}

return(

<div>

<Navbar/>

<div className="page-container">

<div className="card">

<h2>Login</h2>

<input
className="input-field"
placeholder="Email"
value={email}
onChange={(e)=>setEmail(e.target.value)}
/>

<input
className="input-field"
type="password"
placeholder="Password"
value={password}
onChange={(e)=>setPassword(e.target.value)}
/>

<button
className="btn"
onClick={login}
>
Login
</button>

<div className="link">
Not registered yet? <a href="/register">Create Account</a></div>

</div>

</div>

</div>

)

}

export default Login