import { SELECT_QUERY, UPDATE_QUERY } from '../../actions/explorerActions';

const INITIAL_STATE = null;

function selected(state = INITIAL_STATE, action) {
  switch (action.type) {
    case SELECT_QUERY:
      return action.payload ? { ...action.payload, q: action.payload.q } : null;
    case UPDATE_QUERY:
      return action.payload ? { ...state, ...action.payload } : null;
    default:
      return state;
  }
}
export default selected;
