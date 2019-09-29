import axios from 'axios';

export const GET_PATIENTS = 'posts/GET_PATIENTS'
export const GET_PATIENTS_REQUESTED = 'posts/GET_PATIENTS_REQUESTED'
export const GET_PATIENTS_ERR = 'posts/GET_POSTS_ERR'

export const getPatients = () => {
    return dispatch => {
      dispatch({
        type: GET_PATIENTS_REQUESTED
      })

      axios.get("http://localhost:5000/patient").then((res) => {
          console.log("get patients res: ", res);
          dispatch({
              type: GET_PATIENTS,
              payload: res.data
          })
      }).catch(err => {
          console.log(err);
          dispatch({
              type: GET_PATIENTS_ERR
          })
      })
    }
  }