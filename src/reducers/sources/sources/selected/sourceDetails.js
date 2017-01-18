
import { FETCH_SOURCE_DETAILS, SET_FAVORITE_SOURCE } from '../../../../actions/sourceActions';
import { createAsyncReducer } from '../../../../lib/reduxHelpers';

const sourceDetails = createAsyncReducer({
  initialState: {
    object: null,
  },
  action: FETCH_SOURCE_DETAILS,
  handleSuccess: payload => ({
    total: payload.total,
    id: payload.results.id,
    object: payload.results,
  }),
  [SET_FAVORITE_SOURCE]: (payload, state) => ({
    object: { ...state.object, isFavorite: payload.arg[1] },
      // object: payload.results,
  }),
});


export default sourceDetails;
