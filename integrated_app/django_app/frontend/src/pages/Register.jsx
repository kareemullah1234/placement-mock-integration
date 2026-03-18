import {useState} from "react"
import API from "../api/api"
import {useNavigate,Link} from "react-router-dom"

function Register(){

const navigate = useNavigate()

const [form,setForm] = useState({
name:"",
email:"",
password:""
})

const handleChange=(e)=>{
setForm({...form,[e.target.name]:e.target.value})
}

const register = async ()=>{

try{

await API.post("/api/register/",form)

alert("Registration Successful")

navigate("/")

}catch{

alert("Registration Failed")

}

}

return(

<div className="page-container">

<div className="card">

<h2>Register</h2>

<input
className="input-field"
name="name"
placeholder="Name"
onChange={handleChange}
/>

<input
className="input-field"
name="email"
placeholder="Email"
onChange={handleChange}
/>

<input
className="input-field"
name="password"
type="password"
placeholder="Password"
onChange={handleChange}
/>

<button className="btn" onClick={register}>
REGISTER
</button>

<div className="link">
<p>Already registered?</p>
<Link to="/">Login</Link>
</div>

</div>

</div>

)

}

const box={
width:"320px",
margin:"120px auto",
display:"flex",
flexDirection:"column",
gap:"10px"
}

export default Register