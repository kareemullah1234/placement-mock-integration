import { AppBar, Toolbar, Typography, Button, Container } from "@mui/material"
import { useNavigate } from "react-router-dom"

function Layout({children}){

const navigate = useNavigate()

return(

<div>

<AppBar position="static">

<Toolbar>

<Typography
variant="h6"
sx={{flexGrow:1,cursor:"pointer"}}
onClick={()=>navigate("/dashboard")}
>

AI Placement Portal

</Typography>

<Button color="inherit" onClick={()=>navigate("/dashboard")}>
Dashboard
</Button>

<Button color="inherit" onClick={()=>navigate("/jobs")}>
Jobs
</Button>

<Button color="inherit">
Logout
</Button>

</Toolbar>

</AppBar>

<Container sx={{marginTop:"40px"}}>
{children}
</Container>

</div>

)

}

export default Layout