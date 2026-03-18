import {useEffect,useState} from "react"
import AdminNavbar from "../components/AdminNavbar"
import API from "../api/api"

function AdminUsers(){

const [users,setUsers] = useState([])

useEffect(()=>{
fetchUsers()
},[])

const fetchUsers = async () => {

const res = await API.get("/common/admin/users/")
setUsers(res.data.users)

}

return(

<div>

<AdminNavbar/>

<div className="main-container">

<h2>Users</h2>

<table className="admin-table">

<thead>

<tr>
<th>Name</th>
<th>Email</th>
<th>Phone</th>
<th>Resume</th>
</tr>

</thead>

<tbody>

{users.map((user)=>(
<tr key={user.id}>

<td>{user.name}</td>
<td>{user.email}</td>
<td>{user.phone || "Not Added"}</td>

<td>
{user.resume ? (
<a
className="resume-btn"
href={`http://127.0.0.1:8000${user.resume}`}
target="_blank"
>
View Resume
</a>
) : (
"No Resume"
)}
</td>

<td>
<button className="edit-btn">Edit</button>

<button className="delete-btn">Delete</button>
</td>

</tr>
))}

</tbody>

</table>

</div>

</div>

)

}

export default AdminUsers