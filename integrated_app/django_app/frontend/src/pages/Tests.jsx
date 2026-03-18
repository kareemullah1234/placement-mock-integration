import { useParams } from "react-router-dom"

function TestPage(){

const {id} = useParams()

return(

<div style={{padding:"40px"}}>

<h2>Assessment Test</h2>

<p>Application ID: {id}</p>

</div>

)

}

export default TestPage